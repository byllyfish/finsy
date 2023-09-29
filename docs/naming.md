# Names of P4 Entities and Schema Objects

This document lists the names of Finsy classes and shows their corresponding
protobuf classes.

## p4entity.py

- P4TableMatch (Match)  `Iterable[p4r.FieldMatch]`
- P4TableAction (Action)  `p4r.TableAction[action]`
- P4IndirectAction (IndirectAction)  `p4r.TableAction[action_profile_*]`
- P4CounterData  `p4r.CounterData`
- P4MeterConfig  `p4r.MeterConfig`
- P4MeterCounterData  `p4r.MeterCounterData`
- P4Member (P4GroupMember? P4WeightedMember) `p4r.ActionProfileGroup.Member`
- P4ValueSetMember  `Iterable[p4r.FieldMatch]`
- P4TableEntry  `p4r.TableEntry`
- P4ExternEntry  `p4r.ExternEntry`
- P4ActionProfileMember  `p4r.ActionProfileMember`
- P4ActionProfileGroup  `p4r.ActionProfileGroup`
- P4MulticastGroupEntry  `p4r.PacketReplicationEngineEntry[multicast_group_entry]`
- P4CloneSessionEntry  `p4r.PacketReplicationEngineEntry[clone_session_entry]`
- P4DigestEntry  `p4r.DigestEntry`
- P4MeterEntry  `p4r.MeterEntry`
- P4DirectMeterEntry  `p4r.DirectMeterEntry`
- P4CounterEntry  `p4r.CounterEntry`
- P4DirectCounterEntry  `p4r.DirectCounterEntry`
- P4ValueSetEntry  `p4r.ValueSetEntry`
- P4PacketIn  `p4r.StreamMessageResponse[packet]`
- P4PacketOut  `p4r.StreamMessageRequest[packet]`
- P4DigestList  `p4r.StreamMessageResponse[digest]`
- P4DigestListAck  `p4r.StreamMessageRequest[digest_ack]`
- P4IdleTimeoutNotification  `p4r.StreamMessageResponse[idle_timeout_notification]`

### Type Aliases

- _ReplicaType
- P4Weight
- P4WeightedAction

## p4schema.py

### Enums

- P4MatchType  `p4i.MatchField.MatchType`
- P4IdleTimeoutBehavior  `p4i.Table.IdleTimeoutBehavior`
- P4ActionScope  `p4i.ActionRef.Scope`
- P4CounterUnit  `p4i.CounterSpec.Unit`
- P4MeterUnit  `p4i.MeterSpec.Unit`
- P4ConfigResponseType `p4r.GetForwardingPipelineConfigRequest.ResponseType`
- P4ConfigAction `p4r.SetForwardingPipelineConfigRequest.Action`
- P4Atomicity  `p4r.WriteRequest.Atomicity`
- P4UpdateType  `p4r.Update.Type`

### Classes

- P4TypeInfo  `p4t.P4TypeInfo`
- P4Table  `p4i.Table`
- P4ActionParam  `p4i.Action.Param`
- P4Action  `p4i.Action`
- P4ActionRef  `p4i.ActionRef`
- P4ActionProfile  `p4i.ActionProfile`
- P4MatchField  `p4i.MatchField`
- P4ControllerPacketMetadata  `p4i.ControllerPacketMetadata`
- P4CPMetadata  `p4i.ControllerPacketMetadata.Metadata`
- P4DirectCounter  `p4i.DirectCounter`
- P4DirectMeter  `p4i.DirectMeter`
- P4Counter  `p4i.Counter`
- P4Meter  `p4i.Meter`
- P4BitsType  `p4t.P4BitstringLikeTypeSpec`
- P4BoolType  `p4t.P4BoolType`
- P4HeaderType  `p4t.HeaderTypeSpec`
- P4HeaderUnionType  `p4t.P4HeaderUnionTypeSpec`
- P4HeaderStackType  `p4t.P4HeaderStackTypeSpec`
- P4HeaderUnionStackType  `p4t.P4HeaderUnionStackTypeSpec`
- P4StructType  `p4t.P4StructTypeSpec`
- P4TupleType  `p4t.P4TupleTypeSpec`
- P4NewType  `p4t.P4NewTypeSpec`
- P4Register  `p4i.Register`
- P4Digest  `p4i.Digest`
- P4ValueSet  `p4i.ValueSet`
- P4ExternInstance  `p4i.ExternInstance`

