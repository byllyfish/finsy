# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: p4/config/v1/p4types.proto
# Protobuf Python Version: 6.30.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    6,
    30,
    0,
    '',
    'p4/config/v1/p4types.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1ap4/config/v1/p4types.proto\x12\x0cp4.config.v1\"\xa1\x07\n\nP4TypeInfo\x12\x36\n\x07structs\x18\x01 \x03(\x0b\x32%.p4.config.v1.P4TypeInfo.StructsEntry\x12\x36\n\x07headers\x18\x02 \x03(\x0b\x32%.p4.config.v1.P4TypeInfo.HeadersEntry\x12\x41\n\rheader_unions\x18\x03 \x03(\x0b\x32*.p4.config.v1.P4TypeInfo.HeaderUnionsEntry\x12\x32\n\x05\x65nums\x18\x04 \x03(\x0b\x32#.p4.config.v1.P4TypeInfo.EnumsEntry\x12,\n\x05\x65rror\x18\x05 \x01(\x0b\x32\x1d.p4.config.v1.P4ErrorTypeSpec\x12K\n\x12serializable_enums\x18\x06 \x03(\x0b\x32/.p4.config.v1.P4TypeInfo.SerializableEnumsEntry\x12\x39\n\tnew_types\x18\x07 \x03(\x0b\x32&.p4.config.v1.P4TypeInfo.NewTypesEntry\x1aN\n\x0cStructsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12-\n\x05value\x18\x02 \x01(\x0b\x32\x1e.p4.config.v1.P4StructTypeSpec:\x02\x38\x01\x1aN\n\x0cHeadersEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12-\n\x05value\x18\x02 \x01(\x0b\x32\x1e.p4.config.v1.P4HeaderTypeSpec:\x02\x38\x01\x1aX\n\x11HeaderUnionsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x32\n\x05value\x18\x02 \x01(\x0b\x32#.p4.config.v1.P4HeaderUnionTypeSpec:\x02\x38\x01\x1aJ\n\nEnumsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12+\n\x05value\x18\x02 \x01(\x0b\x32\x1c.p4.config.v1.P4EnumTypeSpec:\x02\x38\x01\x1a\x62\n\x16SerializableEnumsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x37\n\x05value\x18\x02 \x01(\x0b\x32(.p4.config.v1.P4SerializableEnumTypeSpec:\x02\x38\x01\x1aL\n\rNewTypesEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12*\n\x05value\x18\x02 \x01(\x0b\x32\x1b.p4.config.v1.P4NewTypeSpec:\x02\x38\x01\"\x83\x05\n\x0eP4DataTypeSpec\x12:\n\tbitstring\x18\x01 \x01(\x0b\x32%.p4.config.v1.P4BitstringLikeTypeSpecH\x00\x12(\n\x04\x62ool\x18\x02 \x01(\x0b\x32\x18.p4.config.v1.P4BoolTypeH\x00\x12.\n\x05tuple\x18\x03 \x01(\x0b\x32\x1d.p4.config.v1.P4TupleTypeSpecH\x00\x12+\n\x06struct\x18\x04 \x01(\x0b\x32\x19.p4.config.v1.P4NamedTypeH\x00\x12+\n\x06header\x18\x05 \x01(\x0b\x32\x19.p4.config.v1.P4NamedTypeH\x00\x12\x31\n\x0cheader_union\x18\x06 \x01(\x0b\x32\x19.p4.config.v1.P4NamedTypeH\x00\x12;\n\x0cheader_stack\x18\x07 \x01(\x0b\x32#.p4.config.v1.P4HeaderStackTypeSpecH\x00\x12\x46\n\x12header_union_stack\x18\x08 \x01(\x0b\x32(.p4.config.v1.P4HeaderUnionStackTypeSpecH\x00\x12)\n\x04\x65num\x18\t \x01(\x0b\x32\x19.p4.config.v1.P4NamedTypeH\x00\x12*\n\x05\x65rror\x18\n \x01(\x0b\x32\x19.p4.config.v1.P4ErrorTypeH\x00\x12\x36\n\x11serializable_enum\x18\x0b \x01(\x0b\x32\x19.p4.config.v1.P4NamedTypeH\x00\x12-\n\x08new_type\x18\x0c \x01(\x0b\x32\x19.p4.config.v1.P4NamedTypeH\x00\x42\x0b\n\ttype_spec\"\x1b\n\x0bP4NamedType\x12\x0c\n\x04name\x18\x01 \x01(\t\"\x0c\n\nP4BoolType\"\r\n\x0bP4ErrorType\"\xc5\x02\n\x17P4BitstringLikeTypeSpec\x12*\n\x03\x62it\x18\x01 \x01(\x0b\x32\x1b.p4.config.v1.P4BitTypeSpecH\x00\x12*\n\x03int\x18\x02 \x01(\x0b\x32\x1b.p4.config.v1.P4IntTypeSpecH\x00\x12\x30\n\x06varbit\x18\x03 \x01(\x0b\x32\x1e.p4.config.v1.P4VarbitTypeSpecH\x00\x12\x13\n\x0b\x61nnotations\x18\x04 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x05 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x06 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotationB\x0b\n\ttype_spec\"!\n\rP4BitTypeSpec\x12\x10\n\x08\x62itwidth\x18\x01 \x01(\x05\"!\n\rP4IntTypeSpec\x12\x10\n\x08\x62itwidth\x18\x01 \x01(\x05\"(\n\x10P4VarbitTypeSpec\x12\x14\n\x0cmax_bitwidth\x18\x01 \x01(\x05\"@\n\x0fP4TupleTypeSpec\x12-\n\x07members\x18\x01 \x03(\x0b\x32\x1c.p4.config.v1.P4DataTypeSpec\"\xa8\x02\n\x10P4StructTypeSpec\x12\x36\n\x07members\x18\x01 \x03(\x0b\x32%.p4.config.v1.P4StructTypeSpec.Member\x12\x13\n\x0b\x61nnotations\x18\x02 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x03 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x04 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\x1aG\n\x06Member\x12\x0c\n\x04name\x18\x01 \x01(\t\x12/\n\ttype_spec\x18\x02 \x01(\x0b\x32\x1c.p4.config.v1.P4DataTypeSpec\"\xb1\x02\n\x10P4HeaderTypeSpec\x12\x36\n\x07members\x18\x01 \x03(\x0b\x32%.p4.config.v1.P4HeaderTypeSpec.Member\x12\x13\n\x0b\x61nnotations\x18\x02 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x03 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x04 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\x1aP\n\x06Member\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x38\n\ttype_spec\x18\x02 \x01(\x0b\x32%.p4.config.v1.P4BitstringLikeTypeSpec\"\xac\x02\n\x15P4HeaderUnionTypeSpec\x12;\n\x07members\x18\x01 \x03(\x0b\x32*.p4.config.v1.P4HeaderUnionTypeSpec.Member\x12\x13\n\x0b\x61nnotations\x18\x02 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x03 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x04 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\x1a\x41\n\x06Member\x12\x0c\n\x04name\x18\x01 \x01(\t\x12)\n\x06header\x18\x02 \x01(\x0b\x32\x19.p4.config.v1.P4NamedType\"P\n\x15P4HeaderStackTypeSpec\x12)\n\x06header\x18\x01 \x01(\x0b\x32\x19.p4.config.v1.P4NamedType\x12\x0c\n\x04size\x18\x02 \x01(\x05\"[\n\x1aP4HeaderUnionStackTypeSpec\x12/\n\x0cheader_union\x18\x01 \x01(\x0b\x32\x19.p4.config.v1.P4NamedType\x12\x0c\n\x04size\x18\x02 \x01(\x05\"D\n\x0cKeyValuePair\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\'\n\x05value\x18\x02 \x01(\x0b\x32\x18.p4.config.v1.Expression\"@\n\x10KeyValuePairList\x12,\n\x08kv_pairs\x18\x01 \x03(\x0b\x32\x1a.p4.config.v1.KeyValuePair\"Z\n\nExpression\x12\x16\n\x0cstring_value\x18\x01 \x01(\tH\x00\x12\x15\n\x0bint64_value\x18\x02 \x01(\x03H\x00\x12\x14\n\nbool_value\x18\x03 \x01(\x08H\x00\x42\x07\n\x05value\"?\n\x0e\x45xpressionList\x12-\n\x0b\x65xpressions\x18\x01 \x03(\x0b\x32\x18.p4.config.v1.Expression\"\xd4\x01\n\x14StructuredAnnotation\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x37\n\x0f\x65xpression_list\x18\x02 \x01(\x0b\x32\x1c.p4.config.v1.ExpressionListH\x00\x12\x36\n\x0ckv_pair_list\x18\x03 \x01(\x0b\x32\x1e.p4.config.v1.KeyValuePairListH\x00\x12\x35\n\x0fsource_location\x18\x04 \x01(\x0b\x32\x1c.p4.config.v1.SourceLocationB\x06\n\x04\x62ody\"<\n\x0eSourceLocation\x12\x0c\n\x04\x66ile\x18\x01 \x01(\t\x12\x0c\n\x04line\x18\x02 \x01(\x05\x12\x0e\n\x06\x63olumn\x18\x03 \x01(\x05\"\x89\x03\n\x0eP4EnumTypeSpec\x12\x34\n\x07members\x18\x01 \x03(\x0b\x32#.p4.config.v1.P4EnumTypeSpec.Member\x12\x13\n\x0b\x61nnotations\x18\x02 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x04 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x03 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\x1a\xab\x01\n\x06Member\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x13\n\x0b\x61nnotations\x18\x02 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x04 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x03 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\"\xe6\x03\n\x1aP4SerializableEnumTypeSpec\x12\x34\n\x0funderlying_type\x18\x01 \x01(\x0b\x32\x1b.p4.config.v1.P4BitTypeSpec\x12@\n\x07members\x18\x02 \x03(\x0b\x32/.p4.config.v1.P4SerializableEnumTypeSpec.Member\x12\x13\n\x0b\x61nnotations\x18\x03 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x05 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x04 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\x1a\xba\x01\n\x06Member\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\x0c\x12\x13\n\x0b\x61nnotations\x18\x03 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x05 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x04 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotation\"\"\n\x0fP4ErrorTypeSpec\x12\x0f\n\x07members\x18\x01 \x03(\t\"\x98\x01\n\x14P4NewTypeTranslation\x12\x0b\n\x03uri\x18\x01 \x01(\t\x12\x16\n\x0csdn_bitwidth\x18\x02 \x01(\x05H\x00\x12\x42\n\nsdn_string\x18\x03 \x01(\x0b\x32,.p4.config.v1.P4NewTypeTranslation.SdnStringH\x00\x1a\x0b\n\tSdnStringB\n\n\x08sdn_type\"\xac\x02\n\rP4NewTypeSpec\x12\x35\n\roriginal_type\x18\x01 \x01(\x0b\x32\x1c.p4.config.v1.P4DataTypeSpecH\x00\x12=\n\x0ftranslated_type\x18\x02 \x01(\x0b\x32\".p4.config.v1.P4NewTypeTranslationH\x00\x12\x13\n\x0b\x61nnotations\x18\x03 \x03(\t\x12:\n\x14\x61nnotation_locations\x18\x05 \x03(\x0b\x32\x1c.p4.config.v1.SourceLocation\x12\x42\n\x16structured_annotations\x18\x04 \x03(\x0b\x32\".p4.config.v1.StructuredAnnotationB\x10\n\x0erepresentationB-Z+github.com/p4lang/p4runtime/go/p4/config/v1b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'p4.config.v1.p4types_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'Z+github.com/p4lang/p4runtime/go/p4/config/v1'
  _globals['_P4TYPEINFO_STRUCTSENTRY']._loaded_options = None
  _globals['_P4TYPEINFO_STRUCTSENTRY']._serialized_options = b'8\001'
  _globals['_P4TYPEINFO_HEADERSENTRY']._loaded_options = None
  _globals['_P4TYPEINFO_HEADERSENTRY']._serialized_options = b'8\001'
  _globals['_P4TYPEINFO_HEADERUNIONSENTRY']._loaded_options = None
  _globals['_P4TYPEINFO_HEADERUNIONSENTRY']._serialized_options = b'8\001'
  _globals['_P4TYPEINFO_ENUMSENTRY']._loaded_options = None
  _globals['_P4TYPEINFO_ENUMSENTRY']._serialized_options = b'8\001'
  _globals['_P4TYPEINFO_SERIALIZABLEENUMSENTRY']._loaded_options = None
  _globals['_P4TYPEINFO_SERIALIZABLEENUMSENTRY']._serialized_options = b'8\001'
  _globals['_P4TYPEINFO_NEWTYPESENTRY']._loaded_options = None
  _globals['_P4TYPEINFO_NEWTYPESENTRY']._serialized_options = b'8\001'
  _globals['_P4TYPEINFO']._serialized_start=45
  _globals['_P4TYPEINFO']._serialized_end=974
  _globals['_P4TYPEINFO_STRUCTSENTRY']._serialized_start=472
  _globals['_P4TYPEINFO_STRUCTSENTRY']._serialized_end=550
  _globals['_P4TYPEINFO_HEADERSENTRY']._serialized_start=552
  _globals['_P4TYPEINFO_HEADERSENTRY']._serialized_end=630
  _globals['_P4TYPEINFO_HEADERUNIONSENTRY']._serialized_start=632
  _globals['_P4TYPEINFO_HEADERUNIONSENTRY']._serialized_end=720
  _globals['_P4TYPEINFO_ENUMSENTRY']._serialized_start=722
  _globals['_P4TYPEINFO_ENUMSENTRY']._serialized_end=796
  _globals['_P4TYPEINFO_SERIALIZABLEENUMSENTRY']._serialized_start=798
  _globals['_P4TYPEINFO_SERIALIZABLEENUMSENTRY']._serialized_end=896
  _globals['_P4TYPEINFO_NEWTYPESENTRY']._serialized_start=898
  _globals['_P4TYPEINFO_NEWTYPESENTRY']._serialized_end=974
  _globals['_P4DATATYPESPEC']._serialized_start=977
  _globals['_P4DATATYPESPEC']._serialized_end=1620
  _globals['_P4NAMEDTYPE']._serialized_start=1622
  _globals['_P4NAMEDTYPE']._serialized_end=1649
  _globals['_P4BOOLTYPE']._serialized_start=1651
  _globals['_P4BOOLTYPE']._serialized_end=1663
  _globals['_P4ERRORTYPE']._serialized_start=1665
  _globals['_P4ERRORTYPE']._serialized_end=1678
  _globals['_P4BITSTRINGLIKETYPESPEC']._serialized_start=1681
  _globals['_P4BITSTRINGLIKETYPESPEC']._serialized_end=2006
  _globals['_P4BITTYPESPEC']._serialized_start=2008
  _globals['_P4BITTYPESPEC']._serialized_end=2041
  _globals['_P4INTTYPESPEC']._serialized_start=2043
  _globals['_P4INTTYPESPEC']._serialized_end=2076
  _globals['_P4VARBITTYPESPEC']._serialized_start=2078
  _globals['_P4VARBITTYPESPEC']._serialized_end=2118
  _globals['_P4TUPLETYPESPEC']._serialized_start=2120
  _globals['_P4TUPLETYPESPEC']._serialized_end=2184
  _globals['_P4STRUCTTYPESPEC']._serialized_start=2187
  _globals['_P4STRUCTTYPESPEC']._serialized_end=2483
  _globals['_P4STRUCTTYPESPEC_MEMBER']._serialized_start=2412
  _globals['_P4STRUCTTYPESPEC_MEMBER']._serialized_end=2483
  _globals['_P4HEADERTYPESPEC']._serialized_start=2486
  _globals['_P4HEADERTYPESPEC']._serialized_end=2791
  _globals['_P4HEADERTYPESPEC_MEMBER']._serialized_start=2711
  _globals['_P4HEADERTYPESPEC_MEMBER']._serialized_end=2791
  _globals['_P4HEADERUNIONTYPESPEC']._serialized_start=2794
  _globals['_P4HEADERUNIONTYPESPEC']._serialized_end=3094
  _globals['_P4HEADERUNIONTYPESPEC_MEMBER']._serialized_start=3029
  _globals['_P4HEADERUNIONTYPESPEC_MEMBER']._serialized_end=3094
  _globals['_P4HEADERSTACKTYPESPEC']._serialized_start=3096
  _globals['_P4HEADERSTACKTYPESPEC']._serialized_end=3176
  _globals['_P4HEADERUNIONSTACKTYPESPEC']._serialized_start=3178
  _globals['_P4HEADERUNIONSTACKTYPESPEC']._serialized_end=3269
  _globals['_KEYVALUEPAIR']._serialized_start=3271
  _globals['_KEYVALUEPAIR']._serialized_end=3339
  _globals['_KEYVALUEPAIRLIST']._serialized_start=3341
  _globals['_KEYVALUEPAIRLIST']._serialized_end=3405
  _globals['_EXPRESSION']._serialized_start=3407
  _globals['_EXPRESSION']._serialized_end=3497
  _globals['_EXPRESSIONLIST']._serialized_start=3499
  _globals['_EXPRESSIONLIST']._serialized_end=3562
  _globals['_STRUCTUREDANNOTATION']._serialized_start=3565
  _globals['_STRUCTUREDANNOTATION']._serialized_end=3777
  _globals['_SOURCELOCATION']._serialized_start=3779
  _globals['_SOURCELOCATION']._serialized_end=3839
  _globals['_P4ENUMTYPESPEC']._serialized_start=3842
  _globals['_P4ENUMTYPESPEC']._serialized_end=4235
  _globals['_P4ENUMTYPESPEC_MEMBER']._serialized_start=4064
  _globals['_P4ENUMTYPESPEC_MEMBER']._serialized_end=4235
  _globals['_P4SERIALIZABLEENUMTYPESPEC']._serialized_start=4238
  _globals['_P4SERIALIZABLEENUMTYPESPEC']._serialized_end=4724
  _globals['_P4SERIALIZABLEENUMTYPESPEC_MEMBER']._serialized_start=4538
  _globals['_P4SERIALIZABLEENUMTYPESPEC_MEMBER']._serialized_end=4724
  _globals['_P4ERRORTYPESPEC']._serialized_start=4726
  _globals['_P4ERRORTYPESPEC']._serialized_end=4760
  _globals['_P4NEWTYPETRANSLATION']._serialized_start=4763
  _globals['_P4NEWTYPETRANSLATION']._serialized_end=4915
  _globals['_P4NEWTYPETRANSLATION_SDNSTRING']._serialized_start=4892
  _globals['_P4NEWTYPETRANSLATION_SDNSTRING']._serialized_end=4903
  _globals['_P4NEWTYPESPEC']._serialized_start=4918
  _globals['_P4NEWTYPESPEC']._serialized_end=5218
# @@protoc_insertion_point(module_scope)
