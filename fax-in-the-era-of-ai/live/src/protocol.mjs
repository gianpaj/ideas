/** All handshake and operation fields travel INSIDE authenticated audio frames. */
import {randomBytes, createHmac, hkdfSync, timingSafeEqual, createHash} from 'node:crypto';

export const TYPES = Object.freeze({HELLO: 1, CHALLENGE: 2, CONFIRM: 3, READY: 4, DATA: 5, RECEIPT: 6, CLOSE: 7});
export const NAMES = Object.fromEntries(Object.entries(TYPES).map(([k, v]) => [v, k]));
const DOMAIN = Buffer.from('AIP-FSK2/one-user/v1\0');
const HASH = data => createHash('sha256').update(data).digest();
const fingerprint = sid => HASH(sid).subarray(0, 8).toString('hex');
const roleFor = type => [TYPES.CHALLENGE, TYPES.READY, TYPES.RECEIPT].includes(type) ? 'responder' : 'initiator';

function tag(key, type, body) {
  return createHmac('sha256', key).update(DOMAIN).update(roleFor(type)).update(body).digest().subarray(0, 16);
}
export function makeMessage(key, type, seq, sid, data = Buffer.alloc(0)) {
  if (sid.length !== 16 || data.length > 80) throw Error('protocol field bound');
  const body = Buffer.alloc(19 + data.length);
  body[0] = type;
  body.writeUInt16BE(seq, 1);
  sid.copy(body, 3);
  data.copy(body, 19);
  return Buffer.concat([body, tag(key, type, body)]);
}
export function parseMessage(raw, key) {
  if (raw.length < 35 || raw.length > 115 || !NAMES[raw[0]]) return null;
  const body = raw.subarray(0, -16);
  if (!timingSafeEqual(tag(key, raw[0], body), raw.subarray(-16))) return null;
  return {type: raw[0], seq: raw.readUInt16BE(1), sid: raw.subarray(3, 19), data: raw.subarray(19, -16)};
}
function derive(psk, sid, nonce) {
  return Buffer.from(hkdfSync('sha256', psk, Buffer.concat([sid, nonce]), DOMAIN, 32));
}

/** No wall-clock timestamps or relay state are inputs to protocol decisions.
 * A local endpoint expires the session using local monotonic deadlines.
 * Single operation/session, cached replies make audio retries idempotent.
 */
export class Session {
  constructor({role, key, data = Buffer.from('hello from a real audio link')}) {
    if (!['initiator', 'responder'].includes(role) || key.length !== 32 || data.length > 64) throw Error('invalid role/key/data (max64UTF8bytes)');
    this.role = role;
    this.key = key;
    this.data = data;
    this.state = role === 'initiator' ? 'NEW' : 'LISTEN';
    this.sid = null;
    this.sessionKey = null;
    this.responses = new Map();
    this.lastOutbound = null;
    this.paired = false;
    this.completed = false;
    this.operationCount = 0;
    this.rejections = 0;
    this.sessionFingerprint = null;
  }
  send(type, seq, data, {root = false} = {}) {
    const raw = makeMessage(root ? this.key : this.sessionKey, type, seq, this.sid, data);
    this.lastOutbound = raw;
    return raw;
  }
  start() {
    if (this.role !== 'initiator' || this.state !== 'NEW') return null;
    this.sid = randomBytes(16); // Fresh caller nonce also identifies this audio session.
    this.sessionFingerprint = fingerprint(this.sid);
    this.state = 'WAIT_CHALLENGE';
    return this.send(TYPES.HELLO, 0, Buffer.alloc(0), {root: true});
  }
  receive(raw) {
    const type = raw[0];
    const root = type === TYPES.HELLO || type === TYPES.CHALLENGE;
    const key = root ? this.key : this.sessionKey;
    const reject = reason => { this.rejections++; return {rejected: reason}; };
    if (!key) return reject('unbound');
    const message = parseMessage(raw, key);
    if (!message || roleFor(type) === this.role) return reject('authentication-or-role');
    if (this.sid && !timingSafeEqual(this.sid, message.sid)) return reject('wrong-session');
    const digest = HASH(raw).toString('hex');
    if (this.responses.has(digest)) return {outbound: this.responses.get(digest), duplicate: true};
    const {seq, sid, data} = message;
    let outbound;
    if (this.role === 'responder' && this.state === 'LISTEN' && type === TYPES.HELLO && seq === 0 && !data.length) {
      this.sid = Buffer.from(sid);
      this.sessionFingerprint = fingerprint(sid);
      const nonce = randomBytes(16);
      this.sessionKey = derive(this.key, this.sid, nonce);
      this.state = 'WAIT_CONFIRM';
      outbound = this.send(TYPES.CHALLENGE, 1, nonce, {root: true});
    } else if (this.role === 'initiator' && this.state === 'WAIT_CHALLENGE' && type === TYPES.CHALLENGE && seq === 1 && data.length === 16) {
      this.sessionKey = derive(this.key, this.sid, data);
      this.state = 'WAIT_READY';
      outbound = this.send(TYPES.CONFIRM, 2);
    } else if (this.role === 'responder' && this.state === 'WAIT_CONFIRM' && type === TYPES.CONFIRM && seq === 2 && !data.length) {
      this.paired = true; // Actual authenticated audio CONFIRM was decoded here.
      this.state = 'WAIT_DATA';
      outbound = this.send(TYPES.READY, 2);
    } else if (this.role === 'initiator' && this.state === 'WAIT_READY' && type === TYPES.READY && seq === 2 && !data.length) {
      this.paired = true; // Sending CONFIRM alone NEVER establishes success.
      this.state = 'WAIT_RECEIPT';
      outbound = this.send(TYPES.DATA, 3, this.data);
    } else if (this.role === 'responder' && this.state === 'WAIT_DATA' && this.paired && type === TYPES.DATA && seq === 3 && data.length <= 64) {
      this.operationCount++;
      this.state = 'WAIT_CLOSE';
      outbound = this.send(TYPES.RECEIPT, 3, Buffer.concat([HASH(data).subarray(0, 16), data]));
    } else if (this.role === 'initiator' && this.state === 'WAIT_RECEIPT' && this.paired && type === TYPES.RECEIPT && seq === 3
               && data.length === 16 + this.data.length && timingSafeEqual(data.subarray(0, 16), HASH(this.data).subarray(0, 16))
               && timingSafeEqual(data.subarray(16), this.data)) {
      this.receiptVerified = true;
      this.state = 'CLOSING';
      outbound = this.send(TYPES.CLOSE, 4);
      this.completed = true;
    } else if (this.role === 'responder' && this.state === 'WAIT_CLOSE' && type === TYPES.CLOSE && seq === 4 && !data.length) {
      this.state = 'DONE';
      this.completed = true;
    } else {
      return reject('phase-sequence-or-shape');
    }
    // Cache only a tiny finite number of authenticated request/response pairs.
    this.responses.set(digest, outbound || null);
    return {outbound, received: NAMES[type], state: this.state, paired: this.paired, completed: this.completed};
  }
  close() {
    this.state = 'CLOSED';
    this.key.fill(0);
    this.sessionKey?.fill(0);
    this.responses.clear();
    this.lastOutbound = null;
  }
}
