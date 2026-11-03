# -*- coding: UTF-8 -*-
# native/demo 切换脚本（当前会话生效；完整变量见 examples/config.env.example）
# 用法：. .\switch_demo.ps1            # 切到 demo 形态一（离线 fakeredis）
#       . .\switch_demo.ps1 -Native    # 切回 native（真实实例，需已配连接变量）

param(
    [switch]$Native
)

if ($Native) {
    $env:REDIS_PROVIDER = "native"
    $env:REDIS_PROVIDER_CONFIG = ""
    Write-Host "REDIS_PROVIDER=native（真实 redis-py 直连）"
} else {
    $env:REDIS_PROVIDER = "acme_demo"
    Write-Host "REDIS_PROVIDER=acme_demo（fakeredis 离线形态）"
}
