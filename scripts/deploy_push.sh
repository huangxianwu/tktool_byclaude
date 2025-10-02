#!/bin/bash
# =============================================================================
# macOS 一键部署推送脚本
# 功能：提交代码 → 推送到GitHub → 触发Windows端自动部署
# 使用：./deploy_push.sh [commit_message]
# =============================================================================

set -e  # 遇到错误立即退出

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$SCRIPT_DIR/deploy_config.json"
LOG_FILE="$SCRIPT_DIR/deploy_push.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

# 检查依赖
check_dependencies() {
    log "检查依赖环境..."
    
    # 检查git
    if ! command -v git &> /dev/null; then
        error "Git 未安装，请先安装 Git"
    fi
    
    # 检查curl
    if ! command -v curl &> /dev/null; then
        error "curl 未安装，请先安装 curl"
    fi
    
    # 检查jq（用于JSON处理）
    if ! command -v jq &> /dev/null; then
        warn "jq 未安装，将使用基础JSON处理"
    fi
    
    log "依赖检查完成"
}

# 读取配置
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        if command -v jq &> /dev/null; then
            REMOTE_BRANCH=$(jq -r '.remote_branch // "main"' "$CONFIG_FILE")
            WINDOWS_SERVER=$(jq -r '.windows_server // ""' "$CONFIG_FILE")
            WEBHOOK_URL=$(jq -r '.webhook_url // ""' "$CONFIG_FILE")
            AUTO_PUSH=$(jq -r '.auto_push // true' "$CONFIG_FILE")
        else
            # 简单的配置读取（无jq时的备选方案）
            REMOTE_BRANCH="main"
            WINDOWS_SERVER=""
            WEBHOOK_URL=""
            AUTO_PUSH=true
        fi
    else
        # 默认配置
        REMOTE_BRANCH="main"
        WINDOWS_SERVER=""
        WEBHOOK_URL=""
        AUTO_PUSH=true
        
        # 创建默认配置文件
        cat > "$CONFIG_FILE" << EOF
{
    "remote_branch": "main",
    "windows_server": "",
    "webhook_url": "",
    "auto_push": true,
    "commit_template": "Deploy: {timestamp}",
    "backup_before_push": true
}
EOF
        info "已创建默认配置文件: $CONFIG_FILE"
    fi
}

# 检查Git状态
check_git_status() {
    log "检查Git仓库状态..."
    
    cd "$PROJECT_ROOT"
    
    # 检查是否在Git仓库中
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error "当前目录不是Git仓库"
    fi
    
    # 检查是否有远程仓库
    if ! git remote get-url origin > /dev/null 2>&1; then
        error "未配置远程仓库origin"
    fi
    
    # 显示当前分支
    CURRENT_BRANCH=$(git branch --show-current)
    info "当前分支: $CURRENT_BRANCH"
    
    # 检查是否有未提交的更改
    if [[ -n $(git status --porcelain) ]]; then
        info "检测到未提交的更改"
        git status --short
        return 0
    else
        warn "没有检测到更改，是否继续推送？(y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            info "用户取消操作"
            exit 0
        fi
    fi
}

# 备份数据库
backup_database() {
    log "备份数据库..."
    
    DB_PATH="$PROJECT_ROOT/instance/app.db"
    if [[ -f "$DB_PATH" ]]; then
        BACKUP_DIR="$PROJECT_ROOT/backups/database"
        mkdir -p "$BACKUP_DIR"
        
        TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
        BACKUP_FILE="$BACKUP_DIR/app_${TIMESTAMP}.db"
        
        cp "$DB_PATH" "$BACKUP_FILE"
        log "数据库已备份到: $BACKUP_FILE"
        
        # 保留最近5个备份
        ls -t "$BACKUP_DIR"/app_*.db | tail -n +6 | xargs -r rm
    else
        warn "数据库文件不存在: $DB_PATH"
    fi
}

# 提交代码
commit_changes() {
    log "提交代码更改..."
    
    cd "$PROJECT_ROOT"
    
    # 获取提交信息
    if [[ -n "$1" ]]; then
        COMMIT_MSG="$1"
    else
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        COMMIT_MSG="Deploy: $TIMESTAMP"
    fi
    
    # 添加所有更改
    git add .
    
    # 提交
    if git commit -m "$COMMIT_MSG"; then
        log "代码提交成功: $COMMIT_MSG"
    else
        warn "没有新的更改需要提交"
    fi
}

# 推送到远程仓库
push_to_remote() {
    log "推送到远程仓库..."
    
    cd "$PROJECT_ROOT"
    
    # 推送到远程分支
    if git push origin "$CURRENT_BRANCH:$REMOTE_BRANCH"; then
        log "代码推送成功到 $REMOTE_BRANCH 分支"
        
        # 获取最新的commit hash
        LATEST_COMMIT=$(git rev-parse HEAD)
        info "最新提交: $LATEST_COMMIT"
        
        return 0
    else
        error "代码推送失败"
    fi
}

# 触发Windows端部署
trigger_windows_deployment() {
    log "触发Windows端部署..."
    
    if [[ -n "$WEBHOOK_URL" ]]; then
        # 通过Webhook触发
        PAYLOAD="{\"ref\":\"refs/heads/$REMOTE_BRANCH\",\"repository\":{\"name\":\"tktool\"},\"head_commit\":{\"id\":\"$LATEST_COMMIT\"}}"
        
        if curl -X POST -H "Content-Type: application/json" -d "$PAYLOAD" "$WEBHOOK_URL" --max-time 30; then
            log "Webhook触发成功"
        else
            warn "Webhook触发失败，Windows端需要手动拉取更新"
        fi
    elif [[ -n "$WINDOWS_SERVER" ]]; then
        # 通过SSH触发（如果配置了Windows服务器）
        warn "SSH触发功能待实现，请在Windows端手动执行更新"
    else
        info "未配置自动触发，请在Windows端手动执行: deploy_manager.bat"
        info "或者配置webhook_url到 $CONFIG_FILE"
    fi
}

# 显示部署状态
show_deployment_status() {
    log "部署完成摘要:"
    echo "=================================="
    echo "项目路径: $PROJECT_ROOT"
    echo "当前分支: $CURRENT_BRANCH"
    echo "目标分支: $REMOTE_BRANCH"
    echo "最新提交: ${LATEST_COMMIT:0:8}"
    echo "推送时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=================================="
    
    if [[ -n "$WINDOWS_SERVER" ]]; then
        echo "Windows服务器: $WINDOWS_SERVER"
        echo "请检查Windows端部署状态"
    fi
}

# 主函数
main() {
    log "开始一键部署推送流程..."
    
    # 检查依赖
    check_dependencies
    
    # 加载配置
    load_config
    
    # 检查Git状态
    check_git_status
    
    # 备份数据库
    backup_database
    
    # 提交代码
    commit_changes "$1"
    
    # 推送到远程
    push_to_remote
    
    # 触发Windows端部署
    trigger_windows_deployment
    
    # 显示状态
    show_deployment_status
    
    log "一键部署推送完成！"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi