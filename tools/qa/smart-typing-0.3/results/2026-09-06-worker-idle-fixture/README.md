# Worker idle notification fixture — 2026-09-06

The required full JVM rerun after `55195f2` ran 713 tests and failed one existing
worker test. Its initial XML and complete failed log are preserved. The fixture
consumed only one of two cold-request stop notifications (preparation and score),
then mistook the remaining notification for completed idle unload.

A held unload latch made that incorrect assumption fail deterministically. The
fixture now drains both initial notifications, holds cleanup, asserts that the
idle task remains active and no completion has arrived, then releases cleanup
and waits for its actual stop. Production worker code is unchanged.

The complete worker class passed, followed by **713/713 JVM tests PASS**. The
red reproduction, scoped green, full green and parsed XML totals are archived.
This passing rerun does not erase the required postcommit failure.
