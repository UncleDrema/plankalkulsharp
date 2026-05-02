.method private static int32 fib(int32 V_0)
{
    .maxstack 16
    .locals init (int32 R_0, int32 Z_0, int32 Z_1, int32 Z_2, int32 Z_3)
    ldc.i4 0
    stloc Z_0
    ldc.i4 1
    stloc Z_1
    ldc.i4 0
    stloc Z_2
WTOP_1:
    ldloc Z_2
    ldarg V_0
    clt
    brfalse WEND_2
    ldloc Z_0
    ldloc Z_1
    add
    stloc Z_3
}
