// Auto-generated CIL assembly from Plankalkül source
.assembly extern System.Runtime { }
.assembly extern System.Console { }
.assembly PlankalkulProgram { }
.module PlankalkulProgram.dll

.class public abstract sealed PlankalkulProgram
{
    .method private static int32 max(int32 V_0, int32 V_1)
    {
        .maxstack 16
        .locals init (int32 Z_1, int32 R_0)
        ldarg V_0
        stloc Z_1
        ldloc Z_1
        ldarg V_1
        clt
        brfalse GEND_1
        ldarg V_1
        stloc Z_1
        GEND_1:
        ldloc Z_1
        stloc R_0
        ldloc R_0
        ret
    }

    .method public static void Main(string[] args)
    {
        .entrypoint
        .maxstack 16
        ldc.i4 0
        ldarg.0
        ldlen
        conv.i4
        bge ARDF_3
        ldarg.0
        ldc.i4 0
        ldelem.ref
        call int32 [System.Runtime]System.Int32::Parse(string)
        br AROK_2
        ARDF_3:
        ldc.i4.0
        AROK_2:
        ldc.i4 1
        ldarg.0
        ldlen
        conv.i4
        bge ARDF_5
        ldarg.0
        ldc.i4 1
        ldelem.ref
        call int32 [System.Runtime]System.Int32::Parse(string)
        br AROK_4
        ARDF_5:
        ldc.i4.0
        AROK_4:
        call int32 PlankalkulProgram::max(int32, int32)
        call void [System.Console]System.Console::WriteLine(int32)
        ret
    }
}
