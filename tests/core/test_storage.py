from biometric_core import storage


def test_add_and_retrieve_template():
    storage.add_template(
        employee_id="EMP001",
        finger_type="right_index",
        keypoints=[{"pt": [1.0, 2.0], "size": 3.0, "angle": 0.0, "response": 0.1, "octave": 0, "class_id": -1}],
        descriptors=[[0.1] * 128],
    )
    result = storage.get_employee_templates("EMP001")
    assert "right_index" in result
    assert len(result["right_index"]) == 1


def test_employee_count():
    assert storage.employee_count() == 0
    storage.add_template("EMP001", "right_index", [], [])
    storage.add_template("EMP002", "left_thumb", [], [])
    assert storage.employee_count() == 2


def test_delete_employee_templates():
    storage.add_template("EMP001", "right_index", [], [])
    assert storage.delete_employee_templates("EMP001") is True
    assert storage.get_employee_templates("EMP001") == {}
    assert storage.delete_employee_templates("EMP001") is False


def test_iter_all_templates_yields_every_entry():
    storage.add_template("EMP001", "right_index", [{"pt": [0, 0], "size": 1, "angle": 0, "response": 0, "octave": 0, "class_id": -1}], [[0.0] * 128])
    storage.add_template("EMP002", "left_thumb", [{"pt": [0, 0], "size": 1, "angle": 0, "response": 0, "octave": 0, "class_id": -1}], [[0.0] * 128])

    seen = list(storage.iter_all_templates())
    employee_ids = {entry[0] for entry in seen}
    assert employee_ids == {"EMP001", "EMP002"}
