#!/bin/bash
# Test all three mock failure modes

echo "=== Testing mock-design-error ==="
rm -f output/*.json
timeout 180 python main_adk.py create --mock-design-error 2>&1 | tee /tmp/test_design.log
echo "Design mode patch plan:"
cat output/patch_plan.json 2>/dev/null | python -m json.tool 2>/dev/null || echo "No patch plan found"
echo ""

echo "=== Testing mock-instruction-error ==="
rm -f output/*.json
timeout 180 python main_adk.py create --mock-instruction-error 2>&1 | tee /tmp/test_instruction.log
echo "Instruction mode patch plan:"
cat output/patch_plan.json 2>/dev/null | python -m json.tool 2>/dev/null || echo "No patch plan found"
echo ""

echo "=== Testing mock-objectives-error ==="
rm -f output/*.json
timeout 180 python main_adk.py create --mock-objectives-error 2>&1 | tee /tmp/test_objectives.log
echo "Objectives mode patch plan:"
cat output/patch_plan.json 2>/dev/null | python -m json.tool 2>/dev/null || echo "No patch plan found"
echo ""

echo "=== Summary ==="
echo "Design error root_cause_type:"
cat output/patch_plan.json 2>/dev/null | grep -o '"root_cause_type": "[^"]*"' || echo "N/A"

echo "Instruction error root_cause_type:"
cat /tmp/test_instruction_patch.json 2>/dev/null | grep -o '"root_cause_type": "[^"]*"' || echo "N/A"

echo "Objectives error root_cause_type:"
cat /tmp/test_objectives_patch.json 2>/dev/null | grep -o '"root_cause_type": "[^"]*"' || echo "N/A"
