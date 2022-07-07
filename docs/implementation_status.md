
# Implementation Status

## P4Runtime

- ❌ ExternEntry
- ✅ TableEntry
    - FieldMatch
        - exact
        - ternary
        - lpm
        - range
        - optional
        - ❌ other
    - TableAction
        - action
        - action_profile_member_id
        - action_profile_group_id
        - action_profile_action_set
- ActionProfileMember
- ActionProfileGroup
- MeterEntry
- DirectMeterEntry
- CounterEntry
- DirectCounterEntry
- PacketReplicationEngineEntry
    - ✅ MulticastGroupEntry
    - CloneSessionEntry
- ❌ ValueSetEntry
- RegisterEntry
- ✅ DigestEntry

- StreamMessageRequest
    - ✅ MasterArbitrationUpdate
    - ✅ PacketOut
    - DigestListAck
    - ❌ Any

- StreamMessageResponse
    - ✅ MasterArbitrationUpdate
    - ✅ PacketIn
    - ✅ DigestList
    - IdleTimeoutNotification
    - ❌ Any
    - ❌ StreamError
        - PacketOutError
        - DigestListAckError
        - StreamOtherError

## P4Info

- PkgInfo
- Table
- Action
- ActionProfile
- Counter
- DirectCounter
- Meter
- DirectMeter
- ControllerPacketMetadata
- ❌ ValueSet
- Register
- Digest
- ❌ Extern

## P4Types

- P4TypeInfo
    - structs
    - headers
    - header_unions
    - enums
    - error
    - serializable_enums
    - new_types
- ❌ StructuredAnnotation

