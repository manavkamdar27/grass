"""Tests of v.dissolve with layer other than 1"""

import json

import grass.script as gs


def test_layer_2(dataset_layer_2):
    """Numeric SQLite aggregate function are accepted

    Additionally, it checks:
    1. generated column names
    2. types of columns
    3. aggregate counts
    """
    dataset = dataset_layer_2
    dissolved_vector = "test_sqlite"
    stats = ["avg", "count", "max", "min", "sum", "total"]
    expected_stats_columns = [
        f"{dataset.float_column_name}_{method}" for method in stats
    ]
    gs.run_command(
        "v.dissolve",
        input=dataset.vector_name,
        layer=2,
        column=dataset.str_column_name,
        output=dissolved_vector,
        aggregate_column=dataset.float_column_name,
        aggregate_method=stats,
        aggregate_backend="sql",
        env=dataset_layer_2.session.env,
    )

    vector_info = gs.vector_info(
        dissolved_vector, layer=2, env=dataset_layer_2.session.env
    )
    assert vector_info["level"] == 2
    assert vector_info["centroids"] == 3
    assert vector_info["areas"] == 3
    assert vector_info["num_dblinks"] == 1
    assert vector_info["attribute_primary_key"] == "cat"

    columns = gs.vector_columns(
        dissolved_vector, layer=2, env=dataset_layer_2.session.env
    )
    assert len(columns) == len(expected_stats_columns) + 2
    assert sorted(columns.keys()) == sorted(
        ["cat", dataset.str_column_name] + expected_stats_columns
    ), "Unexpected autogenerated column names"
    for method, stats_column in zip(stats, expected_stats_columns):
        assert stats_column in columns
        column_info = columns[stats_column]
        correct_type = "integer" if method == "count" else "double precision"
        assert columns[stats_column]["type"].lower() == correct_type, (
            f"{stats_column} has a wrong type"
        )
    assert dataset.str_column_name in columns
    column_info = columns[dataset.str_column_name]
    assert column_info["type"].lower() == "character"

    records = json.loads(
        gs.read_command(
            "v.db.select",
            map=dissolved_vector,
            layer=2,
            format="json",
            env=dataset_layer_2.session.env,
        )
    )["records"]
    ref_unique_values = set(dataset.str_column_values)
    actual_values = [record[dataset.str_column_name] for record in records]
    assert len(actual_values) == len(ref_unique_values)
    assert set(actual_values) == ref_unique_values

    aggregate_n = [record[f"{dataset.float_column_name}_count"] for record in records]
    assert (
        sum(aggregate_n)
        == gs.vector_info(dataset.vector_name, env=dataset_layer_2.session.env)["areas"]
    )
    assert sorted(aggregate_n) == [1, 2, 3]
