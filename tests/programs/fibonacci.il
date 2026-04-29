// Auto-generated CIL assembly from Plankalkül source
.assembly extern System.Runtime { }
.assembly extern System.Console { }
.assembly PlankalkulProgram { }
.module PlankalkulProgram.dll

.class public abstract sealed auto ansi PlankalkulProgram
{
    .method public hidebysig static int32 fib(int32 V_0) cil managed
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
        ldc.i4.0
        ldloc Z_2
        ldarg V_0
        clt
        brfalse WSKIP_4
        pop
        ldc.i4.1
        ldloc Z_0
        ldloc Z_1
        add
        stloc Z_3
        ldloc Z_1
        stloc Z_0
        ldloc Z_3
        stloc Z_1
        ldloc Z_2
        ldc.i4 1
        add
        stloc Z_2
        WSKIP_4:
        brtrue WTOP_1
        ldloc Z_0
        stloc R_0
        ldloc R_0
        ret
    }

    .method public hidebysig static void Main(string[] args) cil managed
    {
        .entrypoint
        .maxstack 16
        ldc.i4 0
        ldarg.0
        ldlen
        conv.i4
        bge ARDF_6
        ldarg.0
        ldc.i4 0
        ldelem.ref
        call int32 [System.Runtime]System.Int32::Parse(string)
        br AROK_5
        ARDF_6:
        ldc.i4.0
        AROK_5:
        call int32 PlankalkulProgram::fib(int32)
        call void [System.Console]System.Console::WriteLine(int32)
        ret
    }
}
