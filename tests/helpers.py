def assert_dicts(dict1, dict2):
    assert len(dict1) == len(dict2)
    for key in dict1:
        assert dict1[key] == dict2[key]
