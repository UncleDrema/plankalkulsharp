// Auto-generated CIL assembly from Plankalkül source
.assembly extern System.Runtime { }
.assembly extern System.Console { }
.assembly PlankalkulProgram { }
.module PlankalkulProgram.dll

.class public abstract sealed PlankalkulProgram
{
    // program P1 fib takes [ResolvedBitSeq(length=8)] results in [ResolvedBitSeq(length=8)] uses {'V0': VarSymbol(kind='V', index=0, resolved_type=ResolvedBitSeq(length=8)), 'R0': VarSymbol(kind='R', index=0, resolved_type=ResolvedBitSeq(length=8)), 'Z0': VarSymbol(kind='Z', index=0, resolved_type=ResolvedBitSeq(length=8)), 'Z1': VarSymbol(kind='Z', index=1, resolved_type=ResolvedBitSeq(length=8)), 'Z2': VarSymbol(kind='Z', index=2, resolved_type=ResolvedBitSeq(length=8)), 'Z3': VarSymbol(kind='Z', index=3, resolved_type=ResolvedBitSeq(length=9))}
    .method private static int32 fib(int32 V_0)
    {
        .maxstack 16
        .locals init (int32 R_0, int32 Z_0, int32 Z_1, int32 Z_2, int32 Z_3)
        // assign 0 to Z0
        ldc.i4 0
        stloc Z_0
        // assign 1 to Z1
        ldc.i4 1
        stloc Z_1
        // assign 0 to Z2
        ldc.i4 0
        stloc Z_2
        WTOP_1:
        // check guard condition
        ldloc Z_2
        ldarg V_0
        clt
        // if false exit loop
        brfalse WEND_2
        // assign Z0 + Z1 to Z3
        ldloc Z_0
        ldloc Z_1
        add
        stloc Z_3
        // assign Z1 to Z0
        ldloc Z_1
        stloc Z_0
        // assign Z3 to Z1
        ldloc Z_3
        stloc Z_1
        // assign Z2 + 1 to Z2
        ldloc Z_2
        ldc.i4 1
        add
        stloc Z_2
        br WTOP_1
        WEND_2:
        // assign Z0 to R0
        ldloc Z_0
        stloc R_0
        // return result
        ldloc R_0
        ret
    }

    .method public static void Main(string[] args)
    {
        .entrypoint
        .maxstack 16
        // if 0 >= args.length goto ARDF_4
        ldc.i4 0
        ldarg.0
        ldlen
        conv.i4
        bge ARDF_4
        // parse argument 0 by loading arg and parsing it
        ldarg.0
        ldc.i4 0
        ldelem.ref
        call int32 [System.Runtime]System.Int32::Parse(string)
        br AROK_3
        ARDF_4:
        ldc.i4.0
        AROK_3:
        call int32 PlankalkulProgram::fib(int32)
        call void [System.Console]System.Console::WriteLine(int32)
        ret
    }
}
