#!/bin/bash
mkdir -p .git/hooks

cat > .git/hooks/post-commit << 'EOF'
#!/bin/bash
echo "🔄 Oracle: incremental reindex after commit"
curl -s -X POST http://localhost:8000/build -H "Content-Type: application/json" -d '{"force": false}' > /dev/null || true
echo "✅ Oracle updated"
EOF

cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
echo "🔄 Oracle: full reindex before push"
curl -s -X POST http://localhost:8000/build -H "Content-Type: application/json" -d '{"force": true}' > /dev/null || true
echo "✅ Oracle fresh"
EOF

chmod +x .git/hooks/post-commit .git/hooks/pre-push
echo "✅ Git hooks installed — Oracle now auto-updates on every commit & push"
