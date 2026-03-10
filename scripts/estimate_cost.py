#!/usr/bin/env python3
"""
DSW 实例成本估算工具
"""

import argparse
import json
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dsw_utils import create_client, get_workspace_id, print_table

try:
    from alibabacloud_pai_dsw20220101 import models as dsw_models
except ImportError:
    print("❌ 请安装: pip install alibabacloud-pai-dsw20220101")
    sys.exit(1)


# 参考价格 (美元/小时，实际价格以官网为准)
# 这些是大致价格，仅供参考
SPEC_PRICES = {
    # CPU 实例
    'ecs.g6.large': 0.097,
    'ecs.g6.xlarge': 0.195,
    'ecs.g6.2xlarge': 0.390,
    'ecs.g6.3xlarge': 0.585,
    'ecs.g6.4xlarge': 0.780,
    'ecs.g6.6xlarge': 1.170,
    'ecs.g6.8xlarge': 1.560,
    'ecs.g6.13xlarge': 2.535,
    'ecs.c6.large': 0.082,
    'ecs.c6.xlarge': 0.165,
    'ecs.c6.2xlarge': 0.330,
    'ecs.c6.4xlarge': 0.660,
    'ecs.r6.large': 0.113,
    'ecs.r6.xlarge': 0.226,
    'ecs.r6.2xlarge': 0.452,
    
    # GPU 实例
    'ecs.gn6v-c8g1.2xlarge': 3.120,  # V100
    'ecs.gn6v-c8g1.4xlarge': 6.240,
    'ecs.gn6v-c8g1.8xlarge': 12.480,
    'ecs.gn6e-c12g1.3xlarge': 4.680,  # V100 32GB
    'ecs.gn7-c13g1.2xlarge': 5.460,   # A10
    'ecs.gn7-c13g1.4xlarge': 10.920,
    'ecs.gn7-c13g1.6xlarge': 16.380,
    'ecs.gn8-c13g1.2xlarge': 7.800,   # A100
    'ecs.gn8-c13g1.4xlarge': 15.600,
    'ecs.gn8-c13g1.8xlarge': 31.200,
    
    # 默认价格
    '_default': 0.100
}


def get_spec_price(spec: str) -> float:
    """获取规格价格"""
    return SPEC_PRICES.get(spec, SPEC_PRICES['_default'])


def estimate_instance_cost(instance: dict) -> dict:
    """
    估算实例成本
    
    Args:
        instance: 实例信息字典
    
    Returns:
        成本估算字典
    """
    spec = instance.get('InstanceType', '')
    status = instance.get('Status', '')
    create_time = instance.get('CreateTime', '')
    
    price_per_hour = get_spec_price(spec)
    
    # 计算运行时间
    if create_time:
        try:
            created = datetime.strptime(create_time[:19], '%Y-%m-%dT%H:%M:%SZ')
            now = datetime.utcnow()
            running_hours = (now - created).total_seconds() / 3600
        except:
            running_hours = 0
    else:
        running_hours = 0
    
    # 已花费金额（假设一直在运行）
    estimated_cost = running_hours * price_per_hour
    
    # 月度估算（假设每天运行24小时）
    monthly_cost = price_per_hour * 24 * 30
    
    return {
        'InstanceId': instance.get('InstanceId', 'N/A'),
        'InstanceName': instance.get('InstanceName', 'N/A'),
        'InstanceType': spec,
        'Status': status,
        'PricePerHour': price_per_hour,
        'RunningHours': round(running_hours, 1),
        'EstimatedCost': round(estimated_cost, 2),
        'MonthlyCost': round(monthly_cost, 2)
    }


def estimate_cost(workspace_id: str = None, region_id: str = None, 
                  format: str = 'table', instance_id: str = None):
    """估算成本"""
    try:
        client = create_client(region_id)
        
        if not workspace_id:
            workspace_id = get_workspace_id()
        
        # 获取实例列表
        request = dsw_models.ListInstancesRequest(
            workspace_id=workspace_id,
            page_number=1,
            page_size=100
        )
        
        response = client.list_instances(request)
        
        if response.status_code != 200:
            print(f"❌ 请求失败: {response.status_code}")
            return
        
        instances = response.body.instances
        
        # 过滤指定实例
        if instance_id:
            instances = [i for i in instances if i.instance_id == instance_id or instance_id in i.instance_id]
        
        # 计算成本
        costs = []
        total_hourly = 0
        total_estimated = 0
        total_monthly = 0
        
        for inst in instances:
            inst_dict = {
                'InstanceId': inst.instance_id,
                'InstanceName': inst.instance_name,
                'InstanceType': inst.ecs_spec,
                'Status': inst.status,
                'CreateTime': inst.gmt_create_time
            }
            
            cost = estimate_instance_cost(inst_dict)
            costs.append(cost)
            
            if inst.status == 'Running':
                total_hourly += cost['PricePerHour']
                total_estimated += cost['EstimatedCost']
            total_monthly += cost['MonthlyCost']
        
        if format == 'json':
            print(json.dumps({
                'instances': costs,
                'summary': {
                    'TotalHourlyRunning': round(total_hourly, 3),
                    'TotalEstimatedCost': round(total_estimated, 2),
                    'TotalMonthlyPotential': round(total_monthly, 2)
                }
            }, indent=2, ensure_ascii=False))
            return
        
        print(f"\n💰 成本估算\n")
        print(f"{'注意: 价格仅供参考，实际价格以阿里云官网为准'}\n")
        
        headers = ['实例名称', '规格', '状态', '每小时', '已运行', '预估花费', '月度预估']
        rows = []
        
        for cost in costs:
            status_str = cost['Status']
            if status_str == 'Running':
                status_str = "✅ 运行中"
            elif status_str == 'Stopped':
                status_str = "⏹️ 已停止"
            else:
                status_str = f"⚠️ {status_str}"
            
            rows.append([
                cost['InstanceName'][:20],
                cost['InstanceType'][:25],
                status_str,
                f"${cost['PricePerHour']:.3f}",
                f"{cost['RunningHours']:.1f}h",
                f"${cost['EstimatedCost']:.2f}",
                f"${cost['MonthlyCost']:.2f}"
            ])
        
        print_table(headers, rows)
        
        print(f"\n📊 汇总:")
        print(f"   运行中实例每小时: ${total_hourly:.3f}")
        print(f"   运行中实例预估花费: ${total_estimated:.2f}")
        print(f"   全部实例月度预估: ${total_monthly:.2f}")
        
        print(f"\n💡 节省建议:")
        if total_hourly > 0:
            print(f"   - 停止闲置实例可节省 ${total_hourly:.3f}/小时")
            print(f"   - 使用竞价实例可节省 60-90%")
            print(f"   - 合理设置自动关机策略")
        
    except Exception as e:
        print(f"❌ 错误: {e}")


def main():
    parser = argparse.ArgumentParser(description='DSW 实例成本估算')
    parser.add_argument('--workspace', '-w', help='工作空间 ID')
    parser.add_argument('--region', '-r', help='区域 ID')
    parser.add_argument('--instance', '-i', help='指定实例 ID')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='输出格式')
    
    args = parser.parse_args()
    
    estimate_cost(
        workspace_id=args.workspace,
        region_id=args.region,
        format=args.format,
        instance_id=args.instance
    )


if __name__ == '__main__':
    main()