#!/bin/bash

echo ""
echo "==========================================="
echo "      AssetOS Release Pipeline"
echo "==========================================="
echo ""

echo "1. Git Status"
git status
echo ""

echo "2. Git Diff"
git diff --stat
echo ""

echo "3. Whitespace Check"
git diff --check || exit 1
echo ""

echo "4. Python Compile"
python -m compileall -q . || exit 1
echo "PASS"
echo ""

echo "5. Ruff"
python -m ruff check .
if [ $? -ne 0 ]; then
    echo "Ruff Failed"
    exit 1
fi
echo ""

echo "6. Pytest"
python -m pytest
if [ $? -ne 0 ]; then
    echo "Pytest Failed"
    exit 1
fi
echo ""

echo "==========================================="
echo " All Quality Checks Passed"
echo "==========================================="
echo ""

read -p "Commit message : " msg

git add .

git commit -m "$msg"

git push origin develop

echo ""
echo "==========================================="
echo " Release Complete"
echo "==========================================="