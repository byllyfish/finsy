# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: p4/config/v1/p4info.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import any_pb2 as google_dot_protobuf_dot_any__pb2
from p4.config.v1 import p4types_pb2 as p4_dot_config_dot_v1_dot_p4types__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x19p4/config/v1/p4info.proto\x12\x0cp4.config.v1\x1a\x19google/protobuf/any.proto\x1a\x1ap4/config/v1/p4types.proto\"\x88\x05\n\x06P4Info\x12\'\n\x08pkg_info\x18\x01 \x01(\x0b\x32\x15.p4.config.v1.PkgInfo\x12#\n\x06tables\x18\x02 \x03(\x0b\x32\x13.p4.config.v1.Table\x12%\n\x07\x61\x63tions\x18\x03 \x03(\x0b\x32\x14.p4.config.v1.Action\x12\x34\n\x0f\x61\x63tion_profiles\x18\x04 \x03(\x0b\x32\x1b.p4.config.v1.ActionProfile\x12\'\n\x08\x63ounters\x18\x05 \x03(\x0b\x32\x15.p4.config.v1.Counter\x12\x34\n\x0f\x64irect_counters\x18\x06 \x03(\x0b\x32\x1b.p4.config.v1.DirectCounter\x12#\n\x06meters\x18\x07 \x03(\x0b\x32\x13.p4.config.v1.Meter\x12\x30\n\rdirect_meters\x18\x08 \x03(\x0b\x32\x19.p4.config.v1.DirectMeter\x12J\n\x1a\x63ontroller_packet_metadata\x18\t \x03(\x0b\x32&.p4.config.v1.ControllerPacketMetadata\x12*\n\nvalue_sets\x18\n \x03(\x0b\x32\x16.p4.config.v1.ValueSet\x12)\n\tregisters\x18\x0b \x03(\x0b\x32\x16.p4.config.v1.Register\x12%\n\x07\x64igests\x18\x0c \x03(\x0b\x32\x14.p4.config.v1.Digest\x12%\n\x07\x65xterns\x18\x64 \x03(\x0b\x32\x14.p4.config.v1.Extern\x12,\n\ttype_info\x18\xc8\x01 \x01(\x0b\x32\x18.p4.config.v1.P4TypeInfo\"3\n\rDocumentation\x12\r\n\x05\x62rief\x18\x01 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x02 \x01(\t\"\xa9\x02\n\x07PkgInfo\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x0f\n\x07version\x18\x02 \x01(\t\x12(\n\x03\x64oc\x18\x03 \x01(\x0b\x32\x1b.p4.config.v1.Documentation\x12\x13\n\x0b\x61nnotations\x18\x04 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\n \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x0c\n\x04\x61rch\x18\x05 \x01(\t\x12\x14\n\x0corganization\x18\x06 \x01(\t\x12\x0f\n\x07\x63ontact\x18\x07 \x01(\t\x12\x0b\n\x03url\x18\x08 \x01(\t\x12\x42\n\x16structured_annotations\x18\t \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\"\x87\x02\n\x05P4Ids\"\xfd\x01\n\x06Prefix\x12\x0f\n\x0bUNSPECIFIED\x10\x00\x12\n\n\x06\x41\x43TION\x10\x01\x12\t\n\x05TABLE\x10\x02\x12\r\n\tVALUE_SET\x10\x03\x12\x15\n\x11\x43ONTROLLER_HEADER\x10\x04\x12\x15\n\x11PSA_EXTERNS_START\x10\x10\x12\x12\n\x0e\x41\x43TION_PROFILE\x10\x11\x12\x0b\n\x07\x43OUNTER\x10\x12\x12\x12\n\x0e\x44IRECT_COUNTER\x10\x13\x12\t\n\x05METER\x10\x14\x12\x10\n\x0c\x44IRECT_METER\x10\x15\x12\x0c\n\x08REGISTER\x10\x16\x12\n\n\x06\x44IGEST\x10\x17\x12\x18\n\x13OTHER_EXTERNS_START\x10\x80\x01\x12\x08\n\x03MAX\x10\xff\x01\"\xf2\x01\n\x08Preamble\x12\n\n\x02id\x18\x01 \x01(\r\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\r\n\x05\x61lias\x18\x03 \x01(\t\x12\x13\n\x0b\x61nnotations\x18\x04 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x07 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12(\n\x03\x64oc\x18\x05 \x01(\x0b\x32\x1b.p4.config.v1.Documentation\x12\x42\n\x16structured_annotations\x18\x06 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\"k\n\x06\x45xtern\x12\x16\n\x0e\x65xtern_type_id\x18\x01 \x01(\r\x12\x18\n\x10\x65xtern_type_name\x18\x02 \x01(\t\x12/\n\tinstances\x18\x03 \x03(\x0b\x32\x1c.p4.config.v1.ExternInstance\"^\n\x0e\x45xternInstance\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12\"\n\x04info\x18\x02 \x01(\x0b\x32\x14.google.protobuf.Any\"\xdc\x03\n\nMatchField\x12\n\n\x02id\x18\x01 \x01(\r\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x13\n\x0b\x61nnotations\x18\x03 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\n \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x10\n\x08\x62itwidth\x18\x04 \x01(\x05\x12\x38\n\nmatch_type\x18\x05 \x01(\x0e\x32\".p4.config.v1.MatchField.MatchTypeH\x00\x12\x1a\n\x10other_match_type\x18\x07 \x01(\tH\x00\x12(\n\x03\x64oc\x18\x06 \x01(\x0b\x32\x1b.p4.config.v1.Documentation\x12,\n\ttype_name\x18\x08 \x01(\x0b\x32\x19.p4.config.v1.P4NamedType\x12\x42\n\x16structured_annotations\x18\t \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\"V\n\tMatchType\x12\x0f\n\x0bUNSPECIFIED\x10\x00\x12\t\n\x05\x45XACT\x10\x02\x12\x07\n\x03LPM\x10\x03\x12\x0b\n\x07TERNARY\x10\x04\x12\t\n\x05RANGE\x10\x05\x12\x0c\n\x08OPTIONAL\x10\x06\x42\x07\n\x05match\"\xc1\x03\n\x05Table\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12.\n\x0cmatch_fields\x18\x02 \x03(\x0b\x32\x18.p4.config.v1.MatchField\x12,\n\x0b\x61\x63tion_refs\x18\x03 \x03(\x0b\x32\x17.p4.config.v1.ActionRef\x12\x1f\n\x17\x63onst_default_action_id\x18\x04 \x01(\r\x12\x19\n\x11implementation_id\x18\x06 \x01(\r\x12\x1b\n\x13\x64irect_resource_ids\x18\x07 \x03(\r\x12\x0c\n\x04size\x18\x08 \x01(\x03\x12\x46\n\x15idle_timeout_behavior\x18\t \x01(\x0e\x32\'.p4.config.v1.Table.IdleTimeoutBehavior\x12\x16\n\x0eis_const_table\x18\n \x01(\x08\x12.\n\x10other_properties\x18\x64 \x01(\x0b\x32\x14.google.protobuf.Any\"9\n\x13IdleTimeoutBehavior\x12\x0e\n\nNO_TIMEOUT\x10\x00\x12\x12\n\x0eNOTIFY_CONTROL\x10\x01\"\x9c\x02\n\tActionRef\x12\n\n\x02id\x18\x01 \x01(\r\x12,\n\x05scope\x18\x03 \x01(\x0e\x32\x1d.p4.config.v1.ActionRef.Scope\x12\x13\n\x0b\x61nnotations\x18\x02 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x05 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x04 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\"@\n\x05Scope\x12\x15\n\x11TABLE_AND_DEFAULT\x10\x00\x12\x0e\n\nTABLE_ONLY\x10\x01\x12\x10\n\x0c\x44\x45\x46\x41ULT_ONLY\x10\x02\"\x81\x03\n\x06\x41\x63tion\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12*\n\x06params\x18\x02 \x03(\x0b\x32\x1a.p4.config.v1.Action.Param\x1a\xa0\x02\n\x05Param\x12\n\n\x02id\x18\x01 \x01(\r\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x13\n\x0b\x61nnotations\x18\x03 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x08 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x10\n\x08\x62itwidth\x18\x04 \x01(\x05\x12(\n\x03\x64oc\x18\x05 \x01(\x0b\x32\x1b.p4.config.v1.Documentation\x12,\n\ttype_name\x18\x06 \x01(\x0b\x32\x19.p4.config.v1.P4NamedType\x12\x42\n\x16structured_annotations\x18\x07 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\"\xa2\x01\n\rActionProfile\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12\x11\n\ttable_ids\x18\x02 \x03(\r\x12\x15\n\rwith_selector\x18\x03 \x01(\x08\x12\x0c\n\x04size\x18\x04 \x01(\x03\x12\x17\n\x0fmax_num_members\x18\x06 \x01(\x03\x12\x16\n\x0emax_group_size\x18\x05 \x01(\x05\"v\n\x0b\x43ounterSpec\x12,\n\x04unit\x18\x01 \x01(\x0e\x32\x1e.p4.config.v1.CounterSpec.Unit\"9\n\x04Unit\x12\x0f\n\x0bUNSPECIFIED\x10\x00\x12\t\n\x05\x42YTES\x10\x01\x12\x0b\n\x07PACKETS\x10\x02\x12\x08\n\x04\x42OTH\x10\x03\"\x9e\x01\n\x07\x43ounter\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12\'\n\x04spec\x18\x02 \x01(\x0b\x32\x19.p4.config.v1.CounterSpec\x12\x0c\n\x04size\x18\x03 \x01(\x03\x12\x32\n\x0findex_type_name\x18\x04 \x01(\x0b\x32\x19.p4.config.v1.P4NamedType\"{\n\rDirectCounter\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12\'\n\x04spec\x18\x02 \x01(\x0b\x32\x19.p4.config.v1.CounterSpec\x12\x17\n\x0f\x64irect_table_id\x18\x03 \x01(\r\"h\n\tMeterSpec\x12*\n\x04unit\x18\x01 \x01(\x0e\x32\x1c.p4.config.v1.MeterSpec.Unit\"/\n\x04Unit\x12\x0f\n\x0bUNSPECIFIED\x10\x00\x12\t\n\x05\x42YTES\x10\x01\x12\x0b\n\x07PACKETS\x10\x02\"\x9a\x01\n\x05Meter\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12%\n\x04spec\x18\x02 \x01(\x0b\x32\x17.p4.config.v1.MeterSpec\x12\x0c\n\x04size\x18\x03 \x01(\x03\x12\x32\n\x0findex_type_name\x18\x04 \x01(\x0b\x32\x19.p4.config.v1.P4NamedType\"w\n\x0b\x44irectMeter\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12%\n\x04spec\x18\x02 \x01(\x0b\x32\x17.p4.config.v1.MeterSpec\x12\x17\n\x0f\x64irect_table_id\x18\x03 \x01(\r\"\x83\x03\n\x18\x43ontrollerPacketMetadata\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12\x41\n\x08metadata\x18\x02 \x03(\x0b\x32/.p4.config.v1.ControllerPacketMetadata.Metadata\x1a\xf9\x01\n\x08Metadata\x12\n\n\x02id\x18\x01 \x01(\r\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x13\n\x0b\x61nnotations\x18\x03 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x07 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x10\n\x08\x62itwidth\x18\x04 \x01(\x05\x12,\n\ttype_name\x18\x05 \x01(\x0b\x32\x19.p4.config.v1.P4NamedType\x12\x42\n\x16structured_annotations\x18\x06 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\"k\n\x08ValueSet\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12\'\n\x05match\x18\x02 \x03(\x0b\x32\x18.p4.config.v1.MatchField\x12\x0c\n\x04size\x18\x03 \x01(\x05\"\xa7\x01\n\x08Register\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12/\n\ttype_spec\x18\x02 \x01(\x0b\x32\x1c.p4.config.v1.P4DataTypeSpec\x12\x0c\n\x04size\x18\x03 \x01(\x05\x12\x32\n\x0findex_type_name\x18\x04 \x01(\x0b\x32\x19.p4.config.v1.P4NamedType\"c\n\x06\x44igest\x12(\n\x08preamble\x18\x01 \x01(\x0b\x32\x16.p4.config.v1.Preamble\x12/\n\ttype_spec\x18\x02 \x01(\x0b\x32\x1c.p4.config.v1.P4DataTypeSpecB-Z+github.com/p4lang/p4runtime/go/p4/config/v1b\x06proto3')



_P4INFO = DESCRIPTOR.message_types_by_name['P4Info']
_DOCUMENTATION = DESCRIPTOR.message_types_by_name['Documentation']
_PKGINFO = DESCRIPTOR.message_types_by_name['PkgInfo']
_P4IDS = DESCRIPTOR.message_types_by_name['P4Ids']
_PREAMBLE = DESCRIPTOR.message_types_by_name['Preamble']
_EXTERN = DESCRIPTOR.message_types_by_name['Extern']
_EXTERNINSTANCE = DESCRIPTOR.message_types_by_name['ExternInstance']
_MATCHFIELD = DESCRIPTOR.message_types_by_name['MatchField']
_TABLE = DESCRIPTOR.message_types_by_name['Table']
_ACTIONREF = DESCRIPTOR.message_types_by_name['ActionRef']
_ACTION = DESCRIPTOR.message_types_by_name['Action']
_ACTION_PARAM = _ACTION.nested_types_by_name['Param']
_ACTIONPROFILE = DESCRIPTOR.message_types_by_name['ActionProfile']
_COUNTERSPEC = DESCRIPTOR.message_types_by_name['CounterSpec']
_COUNTER = DESCRIPTOR.message_types_by_name['Counter']
_DIRECTCOUNTER = DESCRIPTOR.message_types_by_name['DirectCounter']
_METERSPEC = DESCRIPTOR.message_types_by_name['MeterSpec']
_METER = DESCRIPTOR.message_types_by_name['Meter']
_DIRECTMETER = DESCRIPTOR.message_types_by_name['DirectMeter']
_CONTROLLERPACKETMETADATA = DESCRIPTOR.message_types_by_name['ControllerPacketMetadata']
_CONTROLLERPACKETMETADATA_METADATA = _CONTROLLERPACKETMETADATA.nested_types_by_name['Metadata']
_VALUESET = DESCRIPTOR.message_types_by_name['ValueSet']
_REGISTER = DESCRIPTOR.message_types_by_name['Register']
_DIGEST = DESCRIPTOR.message_types_by_name['Digest']
_P4IDS_PREFIX = _P4IDS.enum_types_by_name['Prefix']
_MATCHFIELD_MATCHTYPE = _MATCHFIELD.enum_types_by_name['MatchType']
_TABLE_IDLETIMEOUTBEHAVIOR = _TABLE.enum_types_by_name['IdleTimeoutBehavior']
_ACTIONREF_SCOPE = _ACTIONREF.enum_types_by_name['Scope']
_COUNTERSPEC_UNIT = _COUNTERSPEC.enum_types_by_name['Unit']
_METERSPEC_UNIT = _METERSPEC.enum_types_by_name['Unit']
P4Info = _reflection.GeneratedProtocolMessageType('P4Info', (_message.Message,), {
  'DESCRIPTOR' : _P4INFO,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.P4Info)
  })
_sym_db.RegisterMessage(P4Info)

Documentation = _reflection.GeneratedProtocolMessageType('Documentation', (_message.Message,), {
  'DESCRIPTOR' : _DOCUMENTATION,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.Documentation)
  })
_sym_db.RegisterMessage(Documentation)

PkgInfo = _reflection.GeneratedProtocolMessageType('PkgInfo', (_message.Message,), {
  'DESCRIPTOR' : _PKGINFO,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.PkgInfo)
  })
_sym_db.RegisterMessage(PkgInfo)

P4Ids = _reflection.GeneratedProtocolMessageType('P4Ids', (_message.Message,), {
  'DESCRIPTOR' : _P4IDS,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.P4Ids)
  })
_sym_db.RegisterMessage(P4Ids)

Preamble = _reflection.GeneratedProtocolMessageType('Preamble', (_message.Message,), {
  'DESCRIPTOR' : _PREAMBLE,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.Preamble)
  })
_sym_db.RegisterMessage(Preamble)

Extern = _reflection.GeneratedProtocolMessageType('Extern', (_message.Message,), {
  'DESCRIPTOR' : _EXTERN,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.Extern)
  })
_sym_db.RegisterMessage(Extern)

ExternInstance = _reflection.GeneratedProtocolMessageType('ExternInstance', (_message.Message,), {
  'DESCRIPTOR' : _EXTERNINSTANCE,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.ExternInstance)
  })
_sym_db.RegisterMessage(ExternInstance)

MatchField = _reflection.GeneratedProtocolMessageType('MatchField', (_message.Message,), {
  'DESCRIPTOR' : _MATCHFIELD,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.MatchField)
  })
_sym_db.RegisterMessage(MatchField)

Table = _reflection.GeneratedProtocolMessageType('Table', (_message.Message,), {
  'DESCRIPTOR' : _TABLE,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.Table)
  })
_sym_db.RegisterMessage(Table)

ActionRef = _reflection.GeneratedProtocolMessageType('ActionRef', (_message.Message,), {
  'DESCRIPTOR' : _ACTIONREF,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.ActionRef)
  })
_sym_db.RegisterMessage(ActionRef)

Action = _reflection.GeneratedProtocolMessageType('Action', (_message.Message,), {

  'Param' : _reflection.GeneratedProtocolMessageType('Param', (_message.Message,), {
    'DESCRIPTOR' : _ACTION_PARAM,
    '__module__' : 'p4.config.v1.p4info_pb2'
    # @@protoc_insertion_point(class_scope:p4.config.v1.Action.Param)
    })
  ,
  'DESCRIPTOR' : _ACTION,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.Action)
  })
_sym_db.RegisterMessage(Action)
_sym_db.RegisterMessage(Action.Param)

ActionProfile = _reflection.GeneratedProtocolMessageType('ActionProfile', (_message.Message,), {
  'DESCRIPTOR' : _ACTIONPROFILE,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.ActionProfile)
  })
_sym_db.RegisterMessage(ActionProfile)

CounterSpec = _reflection.GeneratedProtocolMessageType('CounterSpec', (_message.Message,), {
  'DESCRIPTOR' : _COUNTERSPEC,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.CounterSpec)
  })
_sym_db.RegisterMessage(CounterSpec)

Counter = _reflection.GeneratedProtocolMessageType('Counter', (_message.Message,), {
  'DESCRIPTOR' : _COUNTER,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.Counter)
  })
_sym_db.RegisterMessage(Counter)

DirectCounter = _reflection.GeneratedProtocolMessageType('DirectCounter', (_message.Message,), {
  'DESCRIPTOR' : _DIRECTCOUNTER,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.DirectCounter)
  })
_sym_db.RegisterMessage(DirectCounter)

MeterSpec = _reflection.GeneratedProtocolMessageType('MeterSpec', (_message.Message,), {
  'DESCRIPTOR' : _METERSPEC,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.MeterSpec)
  })
_sym_db.RegisterMessage(MeterSpec)

Meter = _reflection.GeneratedProtocolMessageType('Meter', (_message.Message,), {
  'DESCRIPTOR' : _METER,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.Meter)
  })
_sym_db.RegisterMessage(Meter)

DirectMeter = _reflection.GeneratedProtocolMessageType('DirectMeter', (_message.Message,), {
  'DESCRIPTOR' : _DIRECTMETER,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.DirectMeter)
  })
_sym_db.RegisterMessage(DirectMeter)

ControllerPacketMetadata = _reflection.GeneratedProtocolMessageType('ControllerPacketMetadata', (_message.Message,), {

  'Metadata' : _reflection.GeneratedProtocolMessageType('Metadata', (_message.Message,), {
    'DESCRIPTOR' : _CONTROLLERPACKETMETADATA_METADATA,
    '__module__' : 'p4.config.v1.p4info_pb2'
    # @@protoc_insertion_point(class_scope:p4.config.v1.ControllerPacketMetadata.Metadata)
    })
  ,
  'DESCRIPTOR' : _CONTROLLERPACKETMETADATA,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.ControllerPacketMetadata)
  })
_sym_db.RegisterMessage(ControllerPacketMetadata)
_sym_db.RegisterMessage(ControllerPacketMetadata.Metadata)

ValueSet = _reflection.GeneratedProtocolMessageType('ValueSet', (_message.Message,), {
  'DESCRIPTOR' : _VALUESET,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.ValueSet)
  })
_sym_db.RegisterMessage(ValueSet)

Register = _reflection.GeneratedProtocolMessageType('Register', (_message.Message,), {
  'DESCRIPTOR' : _REGISTER,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.Register)
  })
_sym_db.RegisterMessage(Register)

Digest = _reflection.GeneratedProtocolMessageType('Digest', (_message.Message,), {
  'DESCRIPTOR' : _DIGEST,
  '__module__' : 'p4.config.v1.p4info_pb2'
  # @@protoc_insertion_point(class_scope:p4.config.v1.Digest)
  })
_sym_db.RegisterMessage(Digest)

if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'Z+github.com/p4lang/p4runtime/go/p4/config/v1'
  _P4INFO._serialized_start=99
  _P4INFO._serialized_end=747
  _DOCUMENTATION._serialized_start=749
  _DOCUMENTATION._serialized_end=800
  _PKGINFO._serialized_start=803
  _PKGINFO._serialized_end=1100
  _P4IDS._serialized_start=1103
  _P4IDS._serialized_end=1366
  _P4IDS_PREFIX._serialized_start=1113
  _P4IDS_PREFIX._serialized_end=1366
  _PREAMBLE._serialized_start=1369
  _PREAMBLE._serialized_end=1611
  _EXTERN._serialized_start=1613
  _EXTERN._serialized_end=1720
  _EXTERNINSTANCE._serialized_start=1722
  _EXTERNINSTANCE._serialized_end=1816
  _MATCHFIELD._serialized_start=1819
  _MATCHFIELD._serialized_end=2295
  _MATCHFIELD_MATCHTYPE._serialized_start=2200
  _MATCHFIELD_MATCHTYPE._serialized_end=2286
  _TABLE._serialized_start=2298
  _TABLE._serialized_end=2747
  _TABLE_IDLETIMEOUTBEHAVIOR._serialized_start=2690
  _TABLE_IDLETIMEOUTBEHAVIOR._serialized_end=2747
  _ACTIONREF._serialized_start=2750
  _ACTIONREF._serialized_end=3034
  _ACTIONREF_SCOPE._serialized_start=2970
  _ACTIONREF_SCOPE._serialized_end=3034
  _ACTION._serialized_start=3037
  _ACTION._serialized_end=3422
  _ACTION_PARAM._serialized_start=3134
  _ACTION_PARAM._serialized_end=3422
  _ACTIONPROFILE._serialized_start=3425
  _ACTIONPROFILE._serialized_end=3587
  _COUNTERSPEC._serialized_start=3589
  _COUNTERSPEC._serialized_end=3707
  _COUNTERSPEC_UNIT._serialized_start=3650
  _COUNTERSPEC_UNIT._serialized_end=3707
  _COUNTER._serialized_start=3710
  _COUNTER._serialized_end=3868
  _DIRECTCOUNTER._serialized_start=3870
  _DIRECTCOUNTER._serialized_end=3993
  _METERSPEC._serialized_start=3995
  _METERSPEC._serialized_end=4099
  _METERSPEC_UNIT._serialized_start=3650
  _METERSPEC_UNIT._serialized_end=3697
  _METER._serialized_start=4102
  _METER._serialized_end=4256
  _DIRECTMETER._serialized_start=4258
  _DIRECTMETER._serialized_end=4377
  _CONTROLLERPACKETMETADATA._serialized_start=4380
  _CONTROLLERPACKETMETADATA._serialized_end=4767
  _CONTROLLERPACKETMETADATA_METADATA._serialized_start=4518
  _CONTROLLERPACKETMETADATA_METADATA._serialized_end=4767
  _VALUESET._serialized_start=4769
  _VALUESET._serialized_end=4876
  _REGISTER._serialized_start=4879
  _REGISTER._serialized_end=5046
  _DIGEST._serialized_start=5048
  _DIGEST._serialized_end=5147
# @@protoc_insertion_point(module_scope)
