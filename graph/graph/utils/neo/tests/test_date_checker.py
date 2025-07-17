from akcent_graph.utils.neo.date_checker import check_range_in_string


def test_check_range_in_string():
    str1 = '1899'
    str2 = '2025'
    str3 = '2105'
    str4 = ''
    assert check_range_in_string(str1) == 0
    assert check_range_in_string(str2) == 2025
    assert check_range_in_string(str3) == 0
    assert check_range_in_string(str4) == 0
