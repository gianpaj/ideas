from scene_builder_bench.cli import _make_llm_adapter
from scene_builder_bench.registry import project_root
from scene_builder_bench.utils import read_yaml


def test_inception_uses_its_key_and_openai_compatible_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("INCEPTION_API_KEY", "test-inception-key")

    adapter = _make_llm_adapter("inception/mercury-2.5")

    assert adapter.provider == "inception"
    assert adapter.model_name == "mercury-2.5"
    assert adapter.api_key == "test-inception-key"
    assert adapter.base_url == "https://api.inceptionlabs.ai/v1"


def test_cloud_matrix_runs_mercury_first() -> None:
    matrix = read_yaml(project_root() / "configs" / "matrices" / "cloud_providers.yaml")

    assert matrix["models"][0] == {
        "model": "inception/mercury-2.5",
        "label": "mercury-2.5",
    }
