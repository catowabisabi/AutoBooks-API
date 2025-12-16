"""
Django Server Launcher with Debug Information
Run this script to start the Django development server with enhanced logging
"""
import os
import sys
import socket

# Set the project path
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')


def get_local_ip():
    """Get the local IP address for network access"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_startup_info(host: str, port: int):
    """Print debug information about available endpoints"""
    local_ip = get_local_ip()
    
    # Colors for terminal
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    print()
    print(f"{BOLD}{GREEN}{'='*60}{RESET}")
    print(f"{BOLD}{GREEN}  🚀 AutoBooks API Server - Debug Mode{RESET}")
    print(f"{BOLD}{GREEN}{'='*60}{RESET}")
    print()
    
    # Server URLs
    print(f"{BOLD}{CYAN}📡 Server URLs:{RESET}")
    print(f"   Local:      http://127.0.0.1:{port}")
    print(f"   Localhost:  http://localhost:{port}")
    if local_ip != "127.0.0.1":
        print(f"   Network:    http://{local_ip}:{port}")
    print()
    
    # Authentication Endpoints
    print(f"{BOLD}{YELLOW}🔐 Authentication Endpoints:{RESET}")
    print(f"   JWT Login:     POST http://127.0.0.1:{port}/api/v1/auth/token/")
    print(f"   JWT Refresh:   POST http://127.0.0.1:{port}/api/v1/auth/token/refresh/")
    print(f"   Google OAuth:  GET  http://127.0.0.1:{port}/api/v1/auth/google/")
    print(f"   Google Token:  POST http://127.0.0.1:{port}/api/v1/auth/google/token/")
    print()
    
    # Documentation
    print(f"{BOLD}{BLUE}📚 API Documentation:{RESET}")
    print(f"   Swagger UI:    http://127.0.0.1:{port}/api/docs/")
    print(f"   ReDoc:         http://127.0.0.1:{port}/api/redoc/")
    print(f"   OpenAPI JSON:  http://127.0.0.1:{port}/api/schema/")
    print()
    
    # Key Endpoints
    print(f"{BOLD}{CYAN}🔗 Key API Endpoints:{RESET}")
    print(f"   Health Check:  http://127.0.0.1:{port}/api/v1/health/")
    print(f"   Users:         http://127.0.0.1:{port}/api/v1/users/")
    print(f"   Accounting:    http://127.0.0.1:{port}/api/v1/accounting/")
    print(f"   HRMS:          http://127.0.0.1:{port}/api/v1/hrms/")
    print(f"   Projects:      http://127.0.0.1:{port}/api/v1/projects/")
    print(f"   AI Assistants: http://127.0.0.1:{port}/api/v1/ai/")
    print(f"   Analytics:     http://127.0.0.1:{port}/api/v1/analytics/")
    print()
    
    # UI Configuration
    print(f"{BOLD}{GREEN}💡 UI Configuration Tips:{RESET}")
    print(f"   Set in AutoBooks-UI/.env.local:")
    print(f"   NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:{port}")
    print()
    
    # CORS info
    print(f"{BOLD}{YELLOW}⚠️  CORS Configuration:{RESET}")
    print(f"   Ensure your frontend URL is in CORS_ALLOWED_ORIGINS")
    print(f"   Check core/settings.py for CORS settings")
    print()
    
    print(f"{GREEN}{'='*60}{RESET}")
    print()


if __name__ == '__main__':
    # Default port
    port = 8001  # Changed from 8000 to match UI configuration
    host = '0.0.0.0'  # Listen on all interfaces
    
    # Parse command line arguments for custom port
    args = sys.argv[1:]
    if len(args) >= 1 and args[0].isdigit():
        port = int(args[0])
    
    # Print startup info
    print_startup_info(host, port)
    
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'runserver', f'{host}:{port}'])
