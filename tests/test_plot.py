import graphing


def test_static_plot():
    data = graphing.read_file('1.txt')
    assert len(data) > 5
    graphing.plot_intensity(data, axes='yx')