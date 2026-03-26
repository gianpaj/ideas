from scene_planning_bench.registry import load_scene, project_root


def test_load_scene() -> None:
    scene = load_scene(project_root() / "scenes" / "forest_cabin_001.json")
    assert scene.scene_id == "forest_cabin_001"
    assert len(scene.objects) == 2
