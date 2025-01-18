import pytest
import pytest_postgresql


def test_db_access(postgresql):
    cursor = postgresql.cursor()
    cursor.execute("CREATE TABLE test_table (id SERIAL PRIMARY KEY, name VARCHAR(255));")
    cursor.execute("INSERT INTO test_table (name) VALUES ('test');")
    cursor.execute("SELECT * FROM test_table;")
    result = cursor.fetchall()
    assert result == [(1, 'test')]
    cursor.close()
