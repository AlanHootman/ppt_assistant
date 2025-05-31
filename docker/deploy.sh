#!/bin/bash

# PPT助手系统 Docker 部署脚本
# 用法: ./deploy.sh [start|stop|restart|build|logs|status|clean]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和Docker Compose
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    log_info "Docker 和 Docker Compose 检查通过"
}

# 检查LibreOffice (soffice)
check_soffice() {
    log_info "检查LibreOffice安装状态..."
    
    if ! command -v soffice &> /dev/null; then
        log_error "LibreOffice 未安装或 soffice 命令不可用"
        log_warning "PPT助手系统需要LibreOffice来处理和转换PPT文件"
        log_info "请访问以下地址下载并安装LibreOffice:"
        log_info "  https://zh-cn.libreoffice.org/"
        log_info "或者通过命令brew install --cask libreoffice安装"
        log_info ""
        log_info "安装完成后，请确保 soffice 命令可在终端中使用"
        log_info "您可以通过运行 'soffice --version' 来验证安装"
        echo ""
        read -p "是否继续部署? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "部署已取消，请安装LibreOffice后重试"
            exit 1
        fi
        log_warning "继续部署，但PPT处理功能可能无法正常工作"
    else
        # 获取LibreOffice版本信息
        local version=$(soffice --version 2>/dev/null | head -n1 || echo "版本信息获取失败")
        log_success "LibreOffice 已安装: $version"
    fi
}

# 检查环境变量文件
check_env() {
    if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
        log_warning ".env 文件不存在，请先配置环境变量"
        if [[ -f "${PROJECT_ROOT}/.env.example" ]]; then
            log_info "复制 .env.example 到 .env..."
            cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
            log_warning "请编辑 .env 文件配置必要的环境变量（如 OPENAI_API_KEY）"
        else
            log_error "找不到 .env.example 文件"
            exit 1
        fi
    fi
}

# 更新git子模块
update_git_submodules() {
    log_info "更新git子模块..."
    cd "${PROJECT_ROOT}"
    
    # 检查ppt_manager子模块是否存在
    if [[ -d "${PROJECT_ROOT}/libs/ppt_manager" ]]; then
        # 检查是否为空目录
        if [ -z "$(ls -A "${PROJECT_ROOT}/libs/ppt_manager")" ]; then
            log_info "正在初始化并更新ppt_manager子模块..."
            git submodule update --init libs/ppt_manager
        else
            log_info "正在更新ppt_manager子模块..."
            git submodule update libs/ppt_manager
        fi
        
        # 验证子模块更新结果
        if [ -f "${PROJECT_ROOT}/libs/ppt_manager/setup.py" ]; then
            log_success "ppt_manager子模块更新成功"
        else
            log_error "ppt_manager子模块更新失败，setup.py文件不存在"
            log_warning "PPT处理功能可能无法正常工作"
            read -p "是否继续部署? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "部署已取消，请解决子模块问题后重试"
                exit 1
            fi
            log_warning "继续部署，但PPT处理功能可能无法正常工作"
        fi
    else
        log_error "libs/ppt_manager目录不存在，请检查项目结构"
        log_info "尝试初始化子模块..."
        git submodule init
        git submodule update
        
        if [ -d "${PROJECT_ROOT}/libs/ppt_manager" ]; then
            log_success "子模块初始化成功"
        else
            log_error "子模块初始化失败"
            log_warning "PPT处理功能可能无法正常工作"
        fi
    fi
}

# 初始化数据目录
init_data() {
    log_info "初始化数据目录..."
    
    # 检查并创建目标目录
    mkdir -p "${PROJECT_ROOT}/workspace/cache"
    mkdir -p "${PROJECT_ROOT}/workspace/db"
    
    # 1. 拷贝ppt_analysis目录
    if [ -d "${PROJECT_ROOT}/scripts/init_data/ppt_analysis" ]; then
        # 检查目标目录是否为空
        if [ -z "$(ls -A "${PROJECT_ROOT}/workspace/cache/ppt_analysis" 2>/dev/null)" ]; then
            log_info "拷贝初始PPT分析缓存数据..."
            mkdir -p "${PROJECT_ROOT}/workspace/cache/ppt_analysis"
            cp -r "${PROJECT_ROOT}/scripts/init_data/ppt_analysis/"* "${PROJECT_ROOT}/workspace/cache/ppt_analysis/" 2>/dev/null || true
            log_success "PPT分析缓存数据初始化完成"
        else
            log_info "workspace/cache/ppt_analysis目录已有数据，跳过初始化"
        fi
    else
        log_warning "scripts/init_data/ppt_analysis目录不存在，跳过PPT分析缓存初始化"
    fi
    
    # 2. 拷贝db目录
    if [ -d "${PROJECT_ROOT}/scripts/init_data/db" ]; then
        # 检查目标目录是否为空
        if [ -z "$(ls -A "${PROJECT_ROOT}/workspace/db" 2>/dev/null)" ]; then
            log_info "拷贝初始数据库数据..."
            cp -r "${PROJECT_ROOT}/scripts/init_data/db/"* "${PROJECT_ROOT}/workspace/db/" 2>/dev/null || true
            log_success "数据库数据初始化完成"
        else
            log_info "workspace/db目录已有数据，跳过初始化"
        fi
    else
        log_warning "scripts/init_data/db目录不存在，跳过数据库初始化"
    fi
    
    # 设置权限
    chmod -R 755 "${PROJECT_ROOT}/workspace/cache"
    chmod -R 755 "${PROJECT_ROOT}/workspace/db"
}

# 创建必要的目录
setup_directories() {
    log_info "创建必要的目录..."
    
    directories=(
        "${PROJECT_ROOT}/workspace/output"
        "${PROJECT_ROOT}/workspace/logs"
        "${PROJECT_ROOT}/workspace/mlflow"
        "${PROJECT_ROOT}/workspace/redis"
        "${PROJECT_ROOT}/workspace/cache"
        "${PROJECT_ROOT}/workspace/db"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "创建目录: $dir"
        fi
    done
    
    # 设置权限
    chmod -R 755 "${PROJECT_ROOT}/workspace"
    log_success "目录创建完成"
    
    # 初始化数据
    init_data
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    cd "$SCRIPT_DIR"
    docker-compose build --no-cache
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动PPT助手系统..."
    cd "$SCRIPT_DIR"
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    show_status
    
    log_success "PPT助手系统启动完成!"
    log_info "访问地址:"
    log_info "  - 前端界面: http://localhost"
    log_info "  - API文档: http://localhost:8000/docs"
    log_info "  - MLflow: http://localhost:5001"
    log_info "  - MLflow (反向代理): http://localhost/mlflow/"
}

# 停止服务
stop_services() {
    log_info "停止PPT助手系统..."
    cd "$SCRIPT_DIR"
    docker-compose down
    log_success "服务已停止"
}

# 重启服务
restart_services() {
    log_info "重启PPT助手系统..."
    stop_services
    update_git_submodules
    start_services
}

# 显示服务状态
show_status() {
    log_info "服务状态:"
    cd "$SCRIPT_DIR"
    docker-compose ps
}

# 显示日志
show_logs() {
    log_info "显示服务日志 (按 Ctrl+C 退出):"
    cd "$SCRIPT_DIR"
    docker-compose logs -f "${2:-}"
}

# 清理所有数据
clean_all() {
    log_warning "这将删除所有容器、镜像和数据!"
    read -p "确定要继续吗? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "清理Docker资源..."
        cd "$SCRIPT_DIR"
        docker-compose down -v --rmi all
        log_info "清理workspace数据..."
        rm -rf "${PROJECT_ROOT}/workspace"/*
        log_success "清理完成"
    else
        log_info "取消清理操作"
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查服务是否运行
    cd "$SCRIPT_DIR"
    if ! docker-compose ps | grep -q "Up"; then
        log_error "没有运行中的服务"
        return 1
    fi
    
    # 检查LibreOffice
    if command -v soffice &> /dev/null; then
        local version=$(soffice --version 2>/dev/null | head -n1 || echo "版本信息获取失败")
        log_success "LibreOffice 可用: $version"
    else
        log_error "LibreOffice (soffice) 不可用"
        log_warning "PPT处理功能可能无法正常工作"
    fi
    
    # 检查API健康状态
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "API服务健康"
    else
        log_error "API服务不健康"
    fi
    
    # 检查前端
    if curl -f http://localhost > /dev/null 2>&1; then
        log_success "前端服务健康"
    else
        log_error "前端服务不健康"
    fi
    
    # 检查Redis
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis服务健康"
    else
        log_error "Redis服务不健康"
    fi
    
}

# 显示帮助信息
show_help() {
    echo "PPT助手系统 Docker 部署脚本"
    echo ""
    echo "用法:"
    echo "  $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start    - 启动所有服务"
    echo "  stop     - 停止所有服务"
    echo "  restart  - 重启所有服务"
    echo "  build    - 构建Docker镜像"
    echo "  logs     - 显示服务日志"
    echo "  status   - 显示服务状态"
    echo "  health   - 执行健康检查"
    echo "  clean    - 清理所有数据（危险操作）"
    echo "  help     - 显示此帮助信息"
    echo ""
    echo "依赖要求:"
    echo "  - Docker (>= 20.10)"
    echo "  - Docker Compose (>= 2.0)"
    echo "  - LibreOffice (包含 soffice 命令)"
    echo "    下载地址: https://zh-cn.libreoffice.org/"
    echo ""
    echo "示例:"
    echo "  $0 start                    # 启动服务"
    echo "  $0 logs api                # 查看API服务日志"
    echo "  $0 logs                    # 查看所有服务日志"
}

# 主函数
main() {
    case "${1:-help}" in
        start)
            check_docker
            check_env
            update_git_submodules
            setup_directories
            start_services
            ;;
        stop)
            check_docker
            stop_services
            ;;
        restart)
            check_docker
            restart_services
            ;;
        build)
            check_docker
            update_git_submodules
            build_images
            ;;
        logs)
            check_docker
            show_logs "$@"
            ;;
        status)
            check_docker
            show_status
            ;;
        health)
            check_docker
            health_check
            ;;
        clean)
            check_docker
            clean_all
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口
main "$@" 