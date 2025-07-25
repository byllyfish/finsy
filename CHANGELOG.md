# Finsy Change Log

## 0.28.0

- Update `GNMI` protobufs to latest from upstream.
- Re-compile protobuf files with newer `protoc`.
- Re-format python source files with latest version of `black`.

## 0.27.0

- Update `P4Runtime` protobufs to the 1.4.1 release.
- Update dependencies to `grpcio` 1.67.1 and `protobuf` 5.28.3.
- Include CI testing support for Python 3.13.
- In test code, update pytest-asyncio to the latest version.

## 0.26.0

- Replace the `manager` property in the `Switch` class with `stash` and constrain the type to `dict[str, Any]`.
- Add the `stash` keyword argument to the `Switch.__init__` method.
- Remove the `configuration` property from the `SwitchOptions` class. (Use the Switch `stash` property instead.)
- The `control_task` property of the `Switch` class is now private (`_control_task`).
- Add the `pkg_info` accessor to `P4Schema`.
- The `Switch`, `SwitchOptions` and `Controller` classes are now `@final`; they are not intended to be subclassed.
- Update the `protoc` compiler to 1.65.0 and re-compile all protobuf files.
- Update protobuf files from upstream; the `v1.p4info.proto` file now includes the PlatformProperties field in PkgInfo.

## 0.25.0

- The `match_dict`, `match_str` and `action_str` formatting methods now require a P4Schema argument. Removed P4Schema's context manager API. (#499)
- Add support for serializable enums in P4Schema.
- Add port of `flowcache` example that uses serializable enums.
- Add port of basic forwarding example from the P4lang tutorial.
- Re-compile example P4 programs with the latest P4c compiler. Replace file extension `p4info.txt` with  `p4info.txtpb` (#501).
- Make `shellous` an optional dependency that can be installed as an extra: `pip install finsy[demonet]` (#502).
- Fix issue in CI testing which led to an ERROR log message when shutting down GNMIServer testing. (#505)
- When using `black` in CI testing, call it as a library function, not a subprocess. This fixes an occasional thread-related hang on MacOS in CI testing.
- Incorporate the latest changes to `gnmi.proto` and `gnmi_ext.proto`. Upgrade protobuf compiler toolchain and re-compile all protobuf files. Bring "relative path" patch-file up to date.
- Update the demonet docker image: include gpg (for codecov), update ubuntu base tag, and update the mn-stratum base hash. Use latest demonet 24.04 build for CI testing.
- Add the `--with-mac` argument to the `Demonet` class to include the MAC address of hosts when drawing the network map.
- Update doc comments for the Switch, SwitchOptions and Controller classes.
- Improve reliability of CI testing and fix minor typing issues.
- Update dependencies.

## 0.24.0

- Update protobuf dependency and development dependencies.
- Update the demonet image tag used for testing to 24.01.
- Update black formatter to 24.1.1 and re-format source code.

## 0.23.0

- The Demonet class will only run Mininet locally if it detects the script is running inside the special DEMONET docker image.
- Add CI support for Windows.
- Update development dependencies.
- Update publish.yml CI action to use trusted publishing.

## 0.22.0

- Update project dependencies.
- Fix some typing warnings from pyright.

## 0.21.0

- Update P4Runtime protobuf files.
- Add the `metadata` property to `P4MulticastGroupEntry`.
- Update project dependencies. Add support for Python 3.12.
- Apply security best practices to CI builds.

## 0.20.0

- Add support for `P4ExternEntry`.
- Add `Match`, `Action` and `IndirectAction` as aliases for `P4TableMatch`, `P4TableAction`, and `P4IndirectAction`.
- The `Controller.remove` method now returns an `asyncio.Event` to signal when a Switch is fully removed.
- Rename the internal `pbuf.py` module to `pbutil.py`.
- Add a CI step to run tests under valgrind/extra-logging to stress test C-based grpc underpinnings.
- Update project dependencies.

## 0.19.0

- Update P4Runtime/P4Info protobuf files; add support for `has_initial_entries` and `is_const`.
- Add support for grpc call credentials.
- Add support for deprecated `controller_metadata` (#192).
- Fix missing imports for `P4MeterEntry`, `P4DirectMeterEntry` and `P4ValueSetEntry`.
- Entity classes now use `slots`.
- Add support for testing GRPC channels that use TLS in `demonet`.
- Use included MACAddress class.
- Remove dependency on pylev.
- Update project dependencies.

## 0.18.0

- Make all protobuf module imports relative.
- Enable CI testing of example programs; re-compile all P4 sources.
- Improve test coverage and fix lint issues.

## 0.17.0

- The `Switch.delete_all` method no longer takes any arguments; use the new `Switch.delete_many` method for wildcard deletes instead.
- The `Switch.delete_all` method now deletes all action profiles.
- Add support for signed/varbit values.
- Add a P4TypeFactory class for use in testing.
- Update example docs to say that both docker and podman are supported.
- Update project dependencies.

## 0.16.0

- Add `GRPCCredentialsTLS` class for improved TLS support.
- Add support for structured annotations in P4Schema.
- Add support for caching and reusing P4Defs as part of P4Schema.
- Add a py.typed file and improve type annotations.
- Add a `devcontainer.json` file for Github Codespace.
- Fix P4TableAction to allow an action that expects some arguments to be encoded with 0 arguments. Used for wildcard reads. (#193)
- The Demonet sub-module now automatically tries docker if podman is not available.
- Replace flake8 with ruff, fix lint issues, and improve testing.

## 0.15.0

- Rename `current_controller()` function to `Controller.current()`.
- Fix `P4Member` API used by `P4ActionProfileGroup` class.
- Add a version of the ngsdn example that uses action profiles instead of "one-shots".
- Many pyright and pylint fixes.

## 0.14.0

- Add the `fail_fast` option to SwitchOptions.
- Add the `finsy.run` helper function to replace common boilerplate.
- Fix a bug during P4Runtime handshake where a non-arbitration response from the switch caused an exception.
- Fix a bug during PacketIn messages when there is no expected metadata in the P4Info schema.
- Changed `delete_all` so it skips over entries in const tables.
- Initial work on the inband network telemetry example.
- The demonet test module now supports drawing an image of the network.
- Update dependency versions.

## 0.13.0

- Initial work on demonet test module which runs Mininet in a podman container (replacing bash script).
- Update p4runtime protobuf definition to latest `Replica.{egress_port => port}` changes.
- Update gNMI protobuf definitions from `0.8.0` to `0.9.0`.

## 0.12.0

- Add convenience accessors to P4CounterEntry and P4DirectCounterEntry.
- Add the tunnel example.
- Make podman scripts compatible with podman 3.4 on ubuntu.
- Update protobuf support for p4testgen.
- Update dependency versions.

## 0.11.0

- Add some typing overloads for `Switch.read()` to improve IDE experience.
- Annotate the details in a `P4ClientError` exception from a failed WriteRequest.
- Improve support for displaying match/action information as plain text.
- Add `read_tables` support to example tests.
- Add `P4Entity` marker superclass for P4Entity subclasses.
- Add protobuf support for p4testgen.
- Update dependency versions.

## 0.10.0

- The `Switch.read_digests` method now requires the name of the digest as an argument.
- Fix issues related to parsing GNMI path strings and `to_str` escaping. (#117)
- Fix differences in cancellation behavior in `Controller.run`. (#101)
- Added documentation comments and pylint fixes.

## 0.9.0

- Rename gNMI classes to start with "GNMI" instead of "gNMI".
- Rename `is_no_pipeline_configured` property to `is_pipeline_missing`.
- Rename `P4Status` to `P4RpcStatus`.
- Rename `P4SubError` to `P4Error`.
- Rename `Port` to `SwitchPort` and `PortList` to `SwitchPortList`.
- GNMIClient.set(): argument is now a sequence of 2-tuples.
- Add GNMI example programs. 
- Minor test changes to improve code coverage.
- Minor pyright fixes.
- Update dependency versions.
- Build API docs.

## 0.8.0

- Update `gnmi.proto`, `p4info.proto` protobuf files. Re-compile using latest mypy-protobuf compiler.
- Rename `SwitchOptions.config` to `configuration`.
- Rename `Switch.attachment` to `manager`.
- Add support for P4Runtime roles using `p4_role_config.proto` from Stratum project.
- Add support for `@format` address annotations in P4 source code.
- Remove `TRACE` decorator scaffolding.
- Add support for Python 3.11 in tests.
- Add tests for example programs.

## 0.7.0

- Automatically promote a `P4TableAction` in an indirect table to a single-entry one-shot `P4IndirectAction`.
- Add syntactic sugar for "weighted table actions" using the `*` operator.
- Fix bug in parsing annotations which contain newline characters.
- Add support for new_type's in match fields, action parameters and ControllerPacketMetadata.
- Add type_name accessor for custom types in P4Schema.
- Remove support for annotation source locations (filename, lineno); no anticipated use cases.
- Add support for range match field type.
- Remove the `FINSY_TRANSLATE_LOGS` environment variable check.
- Add tests and typing support.
- Update dependency versions.

## 0.6.0

- Rename `ignore_not_found=True` option to `strict=False` in Switch.write(), Switch.modify() and Switch.delete().
- Add the `warn_only=True` option to Switch write() methods.
- Implement support for P4CounterEntry.
- Add the ack() convenience method to `P4DigestList` class.
- Add a convenience accessor to `P4TableEntry` to retrieve match parameters.
- The `Switch.delete_all()` method now takes an optional parameter to support wildcard deletes.
- The `Controller` class can now be run as an asynchronous context manager.
- Add the `is_up` and `address` property getters to the Switch class.
- Add support for exercise 6 (SRv6) to the ngsdn demo.
- Add a simple console module to the ngsdn demo.
- Improve support for formatting P4TableEntry's in a concise manner, used in ngsdn demo.
- Many improvements to the output of `P4SchemaDescription`.
- Export `finsy.LoggerAdapter()` for use by clients.

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
