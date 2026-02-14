#!/usr/bin/env bash
set -euo >/dev/null 2>&1

source "./global_vars.sh"
source "./common.sh"
source "./cmd.sh"
source "./gen_ssl.sh"
source "./args_handler.sh"
source "./ports_handler.sh"
source "./envfile_handler.sh"
source "./template_handler.sh"
source "./container_handler.sh"
source "./vars_handler.sh"
source "./prompt_handler.sh"
source "./service_handler.sh"
source "./upgrade_handler.sh"
source "./version_handler.sh"

# ==================== Main function ====================
main() {
    parse_args "$@"
    detect_os
    check_software_dependency
    process_env_file
    generate_config_files
    process_all_services
    show_deploy_prompt
}

# Execute main function
main "$@"
