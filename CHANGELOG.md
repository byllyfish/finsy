# Finsy Change Log

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
