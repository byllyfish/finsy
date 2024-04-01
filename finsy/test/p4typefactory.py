"Implement P4TypeFactory helper."

import finsy.p4schema as sch
from finsy.p4values import encode_enum
from finsy.proto import p4t


class P4TypeFactory:
    """Factory class to dynamically construct P4 types during tests.

    Examples:

        factory = P4TypeFactory()
        bool_t = factory.bool_type()
        uint8_t = factory.bits_type(8)
        my_struct = factory.struct_type("my_struct", x=bool_t, y=uint8_t)
        my_enum = factory.serializable_enum("my_enum", 32, X=1, Y=2)
        data = my_struct.encode_data({"x": True, "y": 100})
        print(data)
    """

    _type_info: sch.P4TypeInfo

    def __init__(self):
        self._type_info = sch.P4TypeInfo(p4t.P4TypeInfo())

    def bool_type(self) -> sch.P4BoolType:
        "Construct a `bool` type."
        return sch.P4BoolType(p4t.P4BoolType())

    def bits_type(
        self,
        bitwidth: int,
        *,
        signed: bool = False,
        varbit: bool = False,
    ) -> sch.P4BitsType:
        "Construct a `bits` type, which may be signed or varbit."
        if varbit:
            assert not signed
            return sch.P4BitsType(
                p4t.P4BitstringLikeTypeSpec(
                    varbit=p4t.P4VarbitTypeSpec(max_bitwidth=bitwidth)
                )
            )

        if signed:
            assert not varbit
            return sch.P4BitsType(
                p4t.P4BitstringLikeTypeSpec(int=p4t.P4IntTypeSpec(bitwidth=bitwidth))
            )

        return sch.P4BitsType(
            p4t.P4BitstringLikeTypeSpec(bit=p4t.P4BitTypeSpec(bitwidth=bitwidth))
        )

    def tuple_type(self, *members: sch.P4Type) -> sch.P4TupleType:
        "Construct a `tuple` type."
        return sch.P4TupleType(
            p4t.P4TupleTypeSpec(members=(member.data_type_spec for member in members)),
            type_info=self._type_info,
        )

    def struct_type(self, __name: str, **members: sch.P4Type) -> sch.P4StructType:
        "Construct a `struct` type."
        result = sch.P4StructType(
            __name,
            p4t.P4StructTypeSpec(
                members=[
                    p4t.P4StructTypeSpec.Member(
                        name=key, type_spec=value.data_type_spec
                    )
                    for key, value in members.items()
                ]
            ),
        )
        self._type_info.structs[__name] = result
        result._finish_init(self._type_info)  # pyright: ignore[reportPrivateUsage]
        return result

    def serializable_enum_type(
        self,
        __name: str,
        __bitwidth: int,
        **members: int,
    ) -> sch.P4SerializableEnumType:
        "Construct a `serializable_enum` type."
        result = sch.P4SerializableEnumType(
            __name,
            p4t.P4SerializableEnumTypeSpec(
                underlying_type=p4t.P4BitTypeSpec(bitwidth=__bitwidth),
                members=[
                    p4t.P4SerializableEnumTypeSpec.Member(
                        name=name,
                        value=encode_enum(value, __bitwidth),
                    )
                    for name, value in members.items()
                ],
            ),
        )
        self._type_info.serializable_enums[__name] = result
        return result
