# Finsy Change Log

## 0.2.0

- Update to latest P4Runtime 1.4.0-dev .proto files from https://github.com/p4lang/p4runtime (13f0d02).
- gNMI API improvements.
  - Make gNMIPath more pythonic. Rename gNMIPath.key() to set().
  - Implement gNMI Set requests.
  - The gNMIClient API now uses a gNMIUpdate class, instead of exposing gnmi.Notification.
  - Add a gNMI tutorial.

## 0.1.0

- Initial release to PyPI.
