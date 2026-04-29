// Auto-generated CIL assembly from Plankalkül source
.assembly extern System.Runtime { }
.assembly extern System.Console { }
.assembly PlankalkulProgram { }
.module PlankalkulProgram.dll

.class public abstract sealed auto ansi PlankalkulProgram
{
    .method public hidebysig static int32 quad(int32 V_0) cil managed
    {
        .maxstack 16
        .locals init (int32 R_0, int32 Z_0)
        ldarg V_0
        call int32 PlankalkulProgram::double(int32)
        stloc Z_0
        ldloc Z_0
        call int32 PlankalkulProgram::double(int32)
        stloc R_0
        ldloc R_0
        ret
    }

    .method public hidebysig static int32 double(int32 V_0) cil managed
    {
        .maxstack 16
        .locals init (int32 R_0)
        ldarg V_0
        ldc.i4 2
        mul
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
        bge ARDF_2
        ldarg.0
        ldc.i4 0
        ldelem.ref
        call int32 [System.Runtime]System.Int32::Parse(string)
        br AROK_1
        ARDF_2:
        ldc.i4.0
        AROK_1:
        call int32 PlankalkulProgram::quad(int32)
        call void [System.Console]System.Console::WriteLine(int32)
        ret
    }
}
