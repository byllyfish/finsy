# Finsy Change Log

## 0.5.0

- The `delete_all` method will reset any default table entries.
- The Switch context manager API no longer retries connections (wait_for_ready=False).
- Improve logging of P4Runtime version and pipeline information.
- Implement `DecodeFormat` as a bit flag in `p4values.py`.
- Update `hello.p4` demos and fix example code in README.
- Update dependency versions.

## 0.4.0

- Switch API functions: `insert`, `modify`, `delete`, `write` now take a single sequence argument (no more varargs).
- Add support for `P4CloneSessionEntry`, `P4DirectCounterEntry`, and `P4IndirectAction`.
- Add a `ContextVar` to store the controller instance. Use the `current_controller` function to retrieve the current controller object.
- Rename the `SWITCH_DONE` event to `CONTROLLER_LEAVE`. Add a corresponding `CONTROLLER_ENTER` event.
- gNMIClient.synchronize() can be called more than once, if we need to read updates up to the next sync response.
- Add the `full_match` method to `P4TableEntry`.
- Improve support for "don't care" LPM and Ternary match fields.
- Improve formatting of multiline gNMI log messages. Improved log translation of P4Runtime binary values.
- Add the `SWITCH_START` and `SWITCH_STOP` events.
- The `read_packets` method can be called from different tasks with different `eth_type` filters.
- The `UNAVAILABLE` gRPC status is no longer reported as an error, to reduce log noise.
- Improve formatting of `P4SchemaDescription` output.
- Add `ngsdn` example program and podman scripts for testing.
- Small performance improvements after minor benchmarking.
- Update project dependency versions.

## 0.3.0

- Rename Switch `packet_iterator`, `digest_iterator` methods to `read_packets` and `read_digests`.
  - Rename `size` keyword argument to `queue_size`.
- Add Switch `read_idle_timeouts` method.
- Implement `P4IdleTimeoutNotification` and `P4DigestListAck` messages.
- Implement `P4ValueSet` and `P4ValueSetEntry`.
- Add support for `STREAM_ERROR` SwitchEvent.
- Improve support for `P4CounterEntry`, `P4DirectCounterEntry`.
- Improve support for `P4MeterEntry`, `P4DirectMeterEntry`.
- Improve the `delete_all()` method.

## 0.2.0

- Update to latest P4Runtime 1.4.0-dev .proto files from https://github.com/p4lang/p4runtime (13f0d02).
- gNMI API improvements.
  - Make gNMIPath more pythonic. Rename gNMIPath.key() to set().
  - Implement gNMI Set requests.
  - The gNMIClient API now uses a gNMIUpdate class, instead of exposing gnmi.Notification.
  - Add a gNMI tutorial.

## 0.1.0

- Initial release to PyPI.
