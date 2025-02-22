# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.cockroachdb import CockroachdbCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import get_metadata_metrics

from .common import COCKROACHDB_VERSION, assert_metrics
from .utils import get_fixture_path

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment'), requires_py3]


def test_metrics(aggregator, instance, dd_run_check):
    check = CockroachdbCheck('cockroachdb', {}, [instance])
    dd_run_check(check)

    assert_metrics(aggregator)

    aggregator.assert_service_check('cockroachdb.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


# The test below is designed to collect metrics that are not exposed in our e2e environment.
# To collect security metrics, we need to enable TLS and provide certificates. In the future,
# we should create a new environment with TLS enabled.
# The unstable metrics are only available in version 23 of CockroachDB, and as of writing,
# that version is marked as unstable. Once this version is officially released,
# we can remove the fixture and create a new environment for version 23.
# Both fixture files were obtained from a manual setup of CockroachDB.
@pytest.mark.parametrize(
    'fixture',
    [
        ('security'),
        ('unstable'),
    ],
)
def test_fixture_metrics(aggregator, instance, dd_run_check, mock_http_response, fixture):

    mock_http_response(file_path=get_fixture_path('{}_metrics.txt'.format(fixture)))

    check = CockroachdbCheck('cockroachdb', {}, [instance])
    dd_run_check(check)
    assert_metrics(aggregator)

    aggregator.assert_service_check('cockroachdb.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_version_metadata(aggregator, instance, datadog_agent, dd_run_check):
    check = CockroachdbCheck('cockroachdb', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    if COCKROACHDB_VERSION == 'latest':
        m = aggregator._metrics['cockroachdb.build.timestamp'][0]
        # extract version from tags that looks like this: ['tag:v21.2.3', 'go_version:go1.16.6']
        version_label = [t for t in m.tags if 'tag' in t]
        assert len(version_label) == 1
        raw_version = version_label[0].split(':', 1)[1]
    else:
        raw_version = COCKROACHDB_VERSION

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major.lstrip('v'),
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
