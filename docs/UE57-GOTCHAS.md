# UE 5.7 Blueprint MCP Gotchas

These notes are generic Unreal Engine 5.7 Blueprint automation issues that can
cause node creation, pin connection, or pin default setting to fail.

## Function Internal Names

Node creation often requires the internal function name, not the display name.

| Case | Use |
| --- | --- |
| Double math functions | `Add_DoubleDouble`, `Subtract_DoubleDouble`, `Multiply_DoubleDouble`, `GreaterEqual_DoubleDouble` |
| Actor transform functions | `K2_SetActorLocation`, `K2_GetActorLocation`, `K2_AddActorWorldOffset` |

## Static Function Targets

For static library functions, use the class/library name as `target`, not
`self`.

Common examples:

- `KismetMathLibrary`
- `KismetSystemLibrary`
- `GameplayStatics`
- `EnhancedInputLocalPlayerSubsystem`

## Common Pin Names

Pin names are case-sensitive.

| Node | Pin names |
| --- | --- |
| Branch (`K2Node_IfThenElse`) | input `Execute`, input `Condition`, output `Then`, output `Else` |
| CallFunction | input `execute`, output `then`, input `self`, output `ReturnValue`, plus parameter pins |
| Cast (`DynamicCast`) | input `execute`, output `then`, output `CastFailed`, input `Object`, output `As <ClassName>` |
| VariableSet | input `execute`, output `then`, input `<VariableName>`, output `Output_Get` |
| VariableGet | output `<VariableName>` |
| Enhanced Input Action | outputs `Started`, `Triggered`, `Ongoing`, `Canceled`, `Completed`, `ActionValue` |
| GetSubsystemFromPC | input `PlayerController`, output `ReturnValue` |
| Event BeginPlay/Tick | output `then`; Tick also outputs `Delta Seconds` |

Branch exec pins use `Execute`/`Then`, while CallFunction exec pins commonly
use lowercase `execute`/`then`.

## Object Pin Defaults

Object pin defaults usually need a two-segment asset object path:

```text
/Game/Path/AssetName.AssetName
```

The final asset name segment is repeated after the dot.

## Graph Lookup

Macro graphs and collapsed/composite graphs may not be in the same top-level
graph arrays as EventGraph and function graphs. Apply
`patches/macrographs-composite-support.patch` to compatible `UEBlueprintMCP`
sources if named graph lookup misses macros or collapsed graphs.

