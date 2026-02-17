# setup-git-hooks.sh
#!/bin/bash
mkdir -p .git/hooks

cat > .git/hooks/post-commit << 'EOF'
#!/bin/bash
echo "🔄 Oracle: incremental reindex after commit"
curl -s -X POST http://localhost:8000/build -H "Content-Type: application/json" -d '{"force": false}' > /dev/null
echo "✅ Oracle index updated"
EOF

cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
echo "🔄 Oracle: full reindex before push (safety)"
curl -s -X POST http://localhost:8000/build -H "Content-Type: application/json" -d '{"force": true}' > /dev/null
echo "✅ Oracle index fresh for push"
EOF

chmod +x .git/hooks/post-commit .git/hooks/pre-push
echo "Git hooks installed — Oracle now auto-updates on commit/push"
