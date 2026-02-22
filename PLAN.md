# Desktop App V1 Plan — Tauri 2 + Gentle (Alignment)

## 1) Goals (V1)
- Local-first desktop app for podcast/audio editing driven by transcript
- Offline transcription + alignment (no cloud dependency required for V1)
- Clean, fast UI; responsive on large files (1–3h)
- Simple packaging and cross‑platform install (macOS, Windows, Ubuntu)

## 2) V1 Scope (deliberately small)
**Must-have**
- Import audio (wav/mp3/m4a)
- Transcribe audio locally (whisper.cpp)
- Align transcript to audio with Gentle
- Text-editing that removes audio segments (non‑destructive)
- Waveform + playhead scrub
- Export edited audio

**Nice-to-have (defer if needed)**
- Multi‑track support
- Speaker diarization
- Noise reduction / EQ
- Overdub / TTS

---

## 3) High‑level Architecture
**Tauri 2 app**
- **UI (Webview)**: React or Svelte + TypeScript
- **Core (Rust)**: app orchestration, file system, database, job control
- **Native binaries**: whisper.cpp + Gentle (invoked as child processes)

**Local data**
- **SQLite** for project metadata and edit operations
- **File storage** in app data directory

---

## 4) Core Pipeline (V1)
1) **Import Audio**
   - Copy into app data project folder
   - Generate waveform peaks (chunked, cached)

2) **Transcription (whisper.cpp)**
   - Run whisper.cpp on audio
   - Output: segments + plain transcript

3) **Alignment (Gentle)**
   - Feed audio + transcript into Gentle
   - Output: word‑level timestamps + confidence
   - Store alignment in project DB (JSON + indexed word map)

4) **Text Edits → Audio Edits**
   - Edits produce a **cut list** (time ranges)
   - Non‑destructive; audio preserved

5) **Export**
   - Apply cut list + crossfades
   - Render to WAV/MP3 using FFmpeg

---

## 5) Data Model (SQLite)
- **Project**: id, name, created_at
- **Asset**: id, project_id, file_path, duration
- **Transcript**: id, project_id, full_text
- **Alignment**: id, project_id, words[] (start, end, text, conf)
- **Edits**: id, project_id, cut_ranges[], notes
- **Render**: id, project_id, output_path, status

---

## 6) UX Flow
1) Create project → import audio
2) Transcribe → align
3) Show transcript + waveform + playhead
4) User deletes text → app creates cuts
5) Export audio

---

## 7) Performance Strategy
- Process audio in **chunks** (avoid loading full file into memory)
- Cache waveform peaks + alignment in DB
- Background jobs for transcription/alignment
- Progressive UI updates (show transcript as it arrives)

---

## 8) Packaging & Distribution
- Bundle Tauri app + whisper.cpp + gentle binary
- On first run:
  - Download whisper model (tiny/base by default)
  - Verify checksum
- Store models in:
  - macOS: `~/Library/Application Support/<App>/models`
  - Windows: `%APPDATA%\<App>\models`
  - Linux: `~/.local/share/<App>/models`

---

## 9) Risks & Mitigations
- **Gentle accuracy**: may misalign noisy or multi‑speaker audio
  - Mitigate: display confidence + allow manual nudges
- **Large files**: long processing times
  - Mitigate: background jobs + progress UI
- **Cross‑platform packaging**: binary compatibility
  - Mitigate: build CI for mac/win/linux

---

## 10) Milestones (suggested)
**M1: Prototype (1–2 weeks)**
- Tauri shell, audio import, waveform view
- whisper.cpp transcription pipeline

**M2: Alignment + Editing (2–3 weeks)**
- Integrate Gentle, store word timestamps
- Text delete → audio cut list

**M3: Export + Polish (1–2 weeks)**
- FFmpeg export
- Project persistence, basic settings

**M4: Packaging (1 week)**
- Signed installers for mac/win/linux
- Model download + caching

---

## 11) Future Extensions (post‑V1)
- Diarization + speaker labels
- Voice regeneration / TTS
- Cloud sync + collaboration
- Advanced audio tools (EQ, compressor, NR)
