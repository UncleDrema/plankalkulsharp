// Auto-generated CIL assembly from Plankalkül source
.assembly extern System.Runtime { }
.assembly extern System.Console { }
.assembly PlankalkulProgram { }
.module PlankalkulProgram.dll

.class sequential sealed public Rec_0 extends [System.Runtime]System.ValueType
{
    .field public int32 f_0
    .field public int32 f_1
}

.class public abstract sealed PlankalkulProgram
{
    // program P0 test takes [ResolvedBitSeq(length=8), ResolvedBitSeq(length=8)] results in [ResolvedBitSeq(length=8)] uses {'V0': VarSymbol(kind='V', index=0, resolved_type=ResolvedBitSeq(length=8)), 'V1': VarSymbol(kind='V', index=1, resolved_type=ResolvedBitSeq(length=8)), 'R0': VarSymbol(kind='R', index=0, resolved_type=ResolvedBitSeq(length=8)), 'Z0': VarSymbol(kind='Z', index=0, resolved_type=ResolvedArray(size=100, element=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8))))), 'Z1': VarSymbol(kind='Z', index=1, resolved_type=ResolvedBitSeq(length=8)), 'Z2': VarSymbol(kind='Z', index=2, resolved_type=ResolvedBitSeq(length=8)), 'Z3': VarSymbol(kind='Z', index=3, resolved_type=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8))))}
    .method private static int32 test(int32 V_0, int32 V_1)
    {
        .maxstack 16
        .locals init (int32 R_0, valuetype Rec_0[] Z_0, int32 Z_1, int32 Z_2, valuetype Rec_0 Z_3)
        // local array (8.0, 8.0)[100] Z_0
        ldc.i4 100
        newarr valuetype Rec_0
        stloc Z_0
        // assign FuncCall(loc=Loc(line=9, column=2), name='alloc_pool', args=()) to Z0
        call valuetype Rec_0[] PlankalkulProgram::alloc_pool()
        stloc Z_0
        // assign FuncCall(loc=Loc(line=11, column=2), name='create_list', args=(VarRef(loc=Loc(line=11, column=14), kind='Z', index=0, type_ann=None, components=()), VarRef(loc=Loc(line=11, column=18), kind='V', index=0, type_ann=None, components=()))) to Z1
        ldloc Z_0
        ldarg V_0
        call int32 PlankalkulProgram::create_list(valuetype Rec_0[], int32)
        stloc Z_1
        // assign FuncCall(loc=Loc(line=13, column=2), name='reverse_list', args=(VarRef(loc=Loc(line=13, column=15), kind='Z', index=0, type_ann=None, components=()), VarRef(loc=Loc(line=13, column=19), kind='Z', index=1, type_ann=None, components=()))) to Z2
        ldloc Z_0
        ldloc Z_1
        call int32 PlankalkulProgram::reverse_list(valuetype Rec_0[], int32)
        stloc Z_2
        // assign Z0[V1 - 1] to Z3
        ldloc Z_0
        ldarg V_1
        ldc.i4 1
        sub
        ldelem valuetype Rec_0
        stloc Z_3
        // assign Z3[1] to R0
        ldloc Z_3
        ldfld int32 valuetype Rec_0::f_1
        stloc R_0
        // return result
        ldloc R_0
        ret
    }

    // program P1 alloc_pool takes [] results in [ResolvedArray(size=100, element=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8))))] uses {'R0': VarSymbol(kind='R', index=0, resolved_type=ResolvedArray(size=100, element=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8))))), 'Z0': VarSymbol(kind='Z', index=0, resolved_type=ResolvedBitSeq(length=7)), 'Z1': VarSymbol(kind='Z', index=1, resolved_type=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8))))}
    .method private static valuetype Rec_0[] alloc_pool()
    {
        .maxstack 16
        .locals init (valuetype Rec_0[] R_0, int32 Z_0, valuetype Rec_0 Z_1)
        // local array (8.0, 8.0)[100] R_0
        ldc.i4 100
        newarr valuetype Rec_0
        stloc R_0
        // start for Z0 from 0 to 99
        ldc.i4 0
        stloc Z_0
        FTOP_1:
        ldloc Z_0
        ldc.i4 99
        bgt FEND_2
        // assign 0 to Z1[0]
        // load variable address Z_1
        ldloca Z_1
        // store component 0: 0 of type (8.0, 8.0)
        ldc.i4 0
        stfld int32 valuetype Rec_0::f_0
        // assign 0 to Z1[1]
        // load variable address Z_1
        ldloca Z_1
        // store component 0: 1 of type (8.0, 8.0)
        ldc.i4 0
        stfld int32 valuetype Rec_0::f_1
        // assign Z1 to R0[Z0]
        // load array R_0
        ldloc R_0
        // store component 0: Z0 of type 100x(8.0, 8.0)
        // 	calculate array index: Z0
        ldloc Z_0
        // 	calculate value: Z1 of type (8.0, 8.0)
        ldloc Z_1
        // 	store element in array
        stelem valuetype Rec_0
        ldloc Z_0
        ldc.i4.1
        add
        stloc Z_0
        br FTOP_1
        // end for Z0 from 0 to 99
        FEND_2:
        // return result
        ldloc R_0
        ret
    }

    // program P4 create_list takes [ResolvedArray(size=100, element=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8)))), ResolvedBitSeq(length=8)] results in [ResolvedBitSeq(length=8)] uses {'V0': VarSymbol(kind='V', index=0, resolved_type=ResolvedArray(size=100, element=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8))))), 'V1': VarSymbol(kind='V', index=1, resolved_type=ResolvedBitSeq(length=8)), 'R0': VarSymbol(kind='R', index=0, resolved_type=ResolvedBitSeq(length=8)), 'Z0': VarSymbol(kind='Z', index=0, resolved_type=ResolvedBitSeq(length=8)), 'Z1': VarSymbol(kind='Z', index=1, resolved_type=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8))))}
    .method private static int32 create_list(valuetype Rec_0[] V_0, int32 V_1)
    {
        .maxstack 16
        .locals init (int32 R_0, int32 Z_0, valuetype Rec_0 Z_1)
        ldarg V_1
        ldc.i4 100
        cgt
        brfalse GEND_1
        // assign 0 to R0
        ldc.i4 0
        stloc R_0
        GEND_1:
        ldarg V_1
        ldc.i4 0
        cgt
        ldc.i4.0
        ceq
        brfalse GEND_2
        // assign 0 to R0
        ldc.i4 0
        stloc R_0
        GEND_2:
        ldarg V_1
        ldc.i4 0
        cgt
        ldarg V_1
        ldc.i4 100
        cgt
        ldc.i4.0
        ceq
        and
        brfalse GEND_3
        // start for Z0 from 1 to V1
        ldc.i4 1
        stloc Z_0
        FTOP_4:
        ldloc Z_0
        ldarg V_1
        bgt FEND_5
        // assign Z0 to Z1[0]
        // load variable address Z_1
        ldloca Z_1
        // store component 0: 0 of type (8.0, 8.0)
        ldloc Z_0
        stfld int32 valuetype Rec_0::f_0
        ldloc Z_0
        ldarg V_1
        ceq
        ldc.i4.0
        ceq
        brfalse GEND_6
        // assign Z0 + 1 to Z1[1]
        // load variable address Z_1
        ldloca Z_1
        // store component 0: 1 of type (8.0, 8.0)
        ldloc Z_0
        ldc.i4 1
        add
        stfld int32 valuetype Rec_0::f_1
        GEND_6:
        ldloc Z_0
        ldarg V_1
        ceq
        brfalse GEND_7
        // assign 0 to Z1[1]
        // load variable address Z_1
        ldloca Z_1
        // store component 0: 1 of type (8.0, 8.0)
        ldc.i4 0
        stfld int32 valuetype Rec_0::f_1
        GEND_7:
        // assign Z1 to V0[Z0 - 1]
        // load argument V_0
        ldarg V_0
        // store component 0: Z0 - 1 of type 100x(8.0, 8.0)
        // 	calculate array index: Z0 - 1
        ldloc Z_0
        ldc.i4 1
        sub
        // 	calculate value: Z1 of type (8.0, 8.0)
        ldloc Z_1
        // 	store element in array
        stelem valuetype Rec_0
        ldloc Z_0
        ldc.i4.1
        add
        stloc Z_0
        br FTOP_4
        // end for Z0 from 1 to V1
        FEND_5:
        // assign 0 to V0[V1 - 1.1]
        // load argument V_0
        ldarg V_0
        // store component 0: V1 - 1 of type 100x(8.0, 8.0)
        // 	calculate array index: V1 - 1
        ldarg V_1
        ldc.i4 1
        sub
        // load element (8.0, 8.0)
        ldelema valuetype Rec_0
        // store component 1: 1 of type (8.0, 8.0)
        ldc.i4 0
        stfld int32 valuetype Rec_0::f_1
        // assign 1 to R0
        ldc.i4 1
        stloc R_0
        GEND_3:
        // return result
        ldloc R_0
        ret
    }

    // program P5 reverse_list takes [ResolvedArray(size=100, element=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8)))), ResolvedBitSeq(length=8)] results in [ResolvedBitSeq(length=8)] uses {'V0': VarSymbol(kind='V', index=0, resolved_type=ResolvedArray(size=100, element=ResolvedRecord(fields=(ResolvedBitSeq(length=8), ResolvedBitSeq(length=8))))), 'V1': VarSymbol(kind='V', index=1, resolved_type=ResolvedBitSeq(length=8)), 'R0': VarSymbol(kind='R', index=0, resolved_type=ResolvedBitSeq(length=8)), 'Z0': VarSymbol(kind='Z', index=0, resolved_type=ResolvedBitSeq(length=8)), 'Z1': VarSymbol(kind='Z', index=1, resolved_type=ResolvedBitSeq(length=8))}
    .method private static int32 reverse_list(valuetype Rec_0[] V_0, int32 V_1)
    {
        .maxstack 16
        .locals init (int32 R_0, int32 Z_0, int32 Z_1)
        // assign 0 to Z0
        ldc.i4 0
        stloc Z_0
        // assign V0[V1 - 1.1] to Z1
        ldarg V_0
        ldarg V_1
        ldc.i4 1
        sub
        ldelema valuetype Rec_0
        ldfld int32 valuetype Rec_0::f_1
        stloc Z_1
        WTOP_1:
        // check guard condition
        ldloc Z_1
        ldc.i4 0
        ceq
        ldc.i4.0
        ceq
        // if false exit loop
        brfalse WEND_2
        // assign Z0 to V0[V1 - 1.1]
        // load argument V_0
        ldarg V_0
        // store component 0: V1 - 1 of type 100x(8.0, 8.0)
        // 	calculate array index: V1 - 1
        ldarg V_1
        ldc.i4 1
        sub
        // load element (8.0, 8.0)
        ldelema valuetype Rec_0
        // store component 1: 1 of type (8.0, 8.0)
        ldloc Z_0
        stfld int32 valuetype Rec_0::f_1
        // assign V1 to Z0
        ldarg V_1
        stloc Z_0
        // assign Z1 to V1
        ldloc Z_1
        starg V_1
        // assign V0[V1 - 1.1] to Z1
        ldarg V_0
        ldarg V_1
        ldc.i4 1
        sub
        ldelema valuetype Rec_0
        ldfld int32 valuetype Rec_0::f_1
        stloc Z_1
        br WTOP_1
        WEND_2:
        // assign Z0 to V0[V1 - 1.1]
        // load argument V_0
        ldarg V_0
        // store component 0: V1 - 1 of type 100x(8.0, 8.0)
        // 	calculate array index: V1 - 1
        ldarg V_1
        ldc.i4 1
        sub
        // load element (8.0, 8.0)
        ldelema valuetype Rec_0
        // store component 1: 1 of type (8.0, 8.0)
        ldloc Z_0
        stfld int32 valuetype Rec_0::f_1
        // assign V1 to R0
        ldarg V_1
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
        // if 1 >= args.length goto ARDF_6
        ldc.i4 1
        ldarg.0
        ldlen
        conv.i4
        bge ARDF_6
        // parse argument 1 by loading arg and parsing it
        ldarg.0
        ldc.i4 1
        ldelem.ref
        call int32 [System.Runtime]System.Int32::Parse(string)
        br AROK_5
        ARDF_6:
        ldc.i4.0
        AROK_5:
        call int32 PlankalkulProgram::test(int32, int32)
        call void [System.Console]System.Console::WriteLine(int32)
        ret
    }
}
