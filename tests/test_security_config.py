"""Static security checks on the container / compose configuration."""
import os

from _util import ROOT, run_module_tests


def _read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


COMPOSE = _read("compose.yaml")


def test_compose_has_no_privileged_or_host_network():
    assert "privileged" not in COMPOSE
    assert "network_mode: host" not in COMPOSE
    assert "network_mode: \"host\"" not in COMPOSE


def test_compose_does_not_mount_docker_socket():
    assert "/var/run/docker.sock" not in COMPOSE


def test_services_drop_all_caps_and_no_new_privileges():
    assert COMPOSE.count("cap_drop: [ALL]") >= 2
    assert COMPOSE.count("no-new-privileges:true") >= 2


def test_runtime_dataset_mounted_read_only():
    assert "./data:/data:ro" in COMPOSE
    assert "read_only: true" in COMPOSE


def test_validator_not_published_to_host():
    # expose (internal) is allowed; a ports mapping that publishes to the host is not.
    assert "ports:" not in COMPOSE
    assert "expose:" in COMPOSE


def test_network_is_internal():
    assert "internal: true" in COMPOSE


def test_resource_limits_present():
    for limit in ("pids_limit:", "mem_limit:", "cpus:"):
        assert COMPOSE.count(limit) >= 2, limit


def test_answer_key_not_copied_into_validator_image():
    dockerfile = _read("validator", "Dockerfile")
    # No COPY line should reference the private answer key.
    for line in dockerfile.splitlines():
        if line.strip().startswith("COPY"):
            assert "answer_key" not in line, line


def test_answer_key_absent_from_dataset_tree():
    for root, _dirs, files in os.walk(os.path.join(ROOT, "data")):
        for f in files:
            assert "answer_key" not in f, os.path.join(root, f)


def test_dockerignore_excludes_private_key_and_dockerfiles_set_user():
    di = _read(".dockerignore")
    assert "validator/answer_key.private.json" in di
    assert "USER lab" in _read("runtime", "Dockerfile")
    assert "USER validator" in _read("validator", "Dockerfile")


if __name__ == "__main__":
    run_module_tests(dict(globals()))
