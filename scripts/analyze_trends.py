#!/usr/bin/env python3
"""
Analyze resource usage trends for PAI-DSW instances.

This script collects historical resource usage data and generates trend reports
to help identify patterns, anomalies, and optimization opportunities.

Usage:
    python analyze_trends.py [options]

Options:
    --instance <id>         Instance ID (default: current instance)
    --instances <ids>       Comma-separated list of instance IDs
    --all                   Analyze all instances in current workspace
    --days <n>              Number of days to analyze (default: 7)
    --start <date>          Start date (YYYY-MM-DD)
    --end <date>            End date (YYYY-MM-DD)
    --interval <hours>      Collection interval in hours (default: 1)
    --save                  Save collected data to history file
    --load                  Load historical data instead of fetching
    --output <file>         Output file for report (default: stdout)
    --format <type>         Output format: text, json, csv (default: text)
    --compare               Compare with previous period
    --help                  Show this help message

Examples:
    # Analyze current instance for past 7 days
    python analyze_trends.py --days 7

    # Analyze specific instance with custom date range
    python analyze_trends.py --instance dsw-123456 --start 2024-01-01 --end 2024-01-07

    # Analyze all instances and save data
    python analyze_trends.py --all --days 3 --save

    # Generate CSV report
    python analyze_trends.py --instance dsw-123456 --days 7 --format csv --output report.csv

    # Compare with previous week
    python analyze_trends.py --days 7 --compare

History Storage:
    Data is stored in ~/.dsw-history/ directory:
    - metrics_<instance_id>_<date>.json  - Daily metrics snapshots
    - trends_<instance_id>.json          - Aggregated trend data
"""

import os
import sys
import json
import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dsw_utils import create_client, get_current_instance_id
from alibabacloud_pai_dsw20220101 import models as dsw_models

# Metric type mappings
METRIC_TYPE_MAP = {
    'cpu': 'CpuCoreUsage',
    'memory': 'MemoryUsage',
    'gpu': 'GpuCoreUsage',
    'gpu-memory': 'GpuMemoryUsage',
    'network-in': 'NetworkInputRate',
    'network-out': 'NetworkOutputRate',
}

DEFAULT_METRICS = ['cpu', 'memory', 'gpu', 'gpu-memory']

# History storage directory
HISTORY_DIR = Path.home() / '.dsw-history'


class TrendAnalyzer:
    """Analyze resource usage trends for DSW instances."""
    
    def __init__(self, region_id: str = None):
        """Initialize the analyzer."""
        self.client = create_client(region_id)
        self.history_dir = HISTORY_DIR
        self.history_dir.mkdir(exist_ok=True)
    
    def collect_metrics(
        self,
        instance_id: str,
        start_time: datetime,
        end_time: datetime,
        interval_hours: int = 1
    ) -> Dict:
        """
        Collect metrics for an instance over a time range.
        
        Args:
            instance_id: Instance ID
            start_time: Start datetime
            end_time: End datetime
            interval_hours: Collection interval in hours
        
        Returns:
            Dictionary with collected metrics
        """
        data = {
            'instance_id': instance_id,
            'collection_start': start_time.isoformat(),
            'collection_end': end_time.isoformat(),
            'interval_hours': interval_hours,
            'collected_at': datetime.utcnow().isoformat(),
            'samples': []
        }
        
        current = start_time
        while current < end_time:
            next_time = current + timedelta(hours=interval_hours)
            if next_time > end_time:
                next_time = end_time
            
            sample = self._fetch_metrics_sample(
                instance_id,
                current.strftime('%Y-%m-%dT%H:%M:%SZ'),
                next_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            )
            
            sample['sample_time'] = current.isoformat()
            data['samples'].append(sample)
            
            current = next_time
        
        return data
    
    def _fetch_metrics_sample(
        self,
        instance_id: str,
        start_time: str,
        end_time: str
    ) -> Dict:
        """Fetch a single metrics sample."""
        sample = {}
        
        for metric_name, api_metric_type in METRIC_TYPE_MAP.items():
            try:
                request = dsw_models.GetInstanceMetricsRequest(
                    start_time=start_time,
                    end_time=end_time,
                    metric_type=api_metric_type
                )
                
                response = self.client.get_instance_metrics(instance_id, request)
                
                if response.body and hasattr(response.body, 'pod_metrics') and response.body.pod_metrics:
                    for pod in response.body.pod_metrics:
                        if pod.metrics:
                            values = [m.value for m in pod.metrics if m.value is not None]
                            if values:
                                sample[metric_name] = {
                                    'min': min(values),
                                    'max': max(values),
                                    'avg': statistics.mean(values),
                                    'count': len(values)
                                }
            except Exception as e:
                # Silently skip failed metric fetches
                pass
        
        return sample
    
    def analyze_trends(self, data: Dict) -> Dict:
        """
        Analyze collected data for trends.
        
        Args:
            data: Collected metrics data
        
        Returns:
            Trend analysis results
        """
        analysis = {
            'instance_id': data['instance_id'],
            'period': {
                'start': data['collection_start'],
                'end': data['collection_end'],
                'duration_hours': (datetime.fromisoformat(data['collection_end']) - 
                                   datetime.fromisoformat(data['collection_start'])).total_seconds() / 3600
            },
            'metrics': {},
            'patterns': {},
            'recommendations': []
        }
        
        # Aggregate metrics across all samples
        for metric in DEFAULT_METRICS:
            metric_data = self._aggregate_metric(data['samples'], metric)
            if metric_data:
                analysis['metrics'][metric] = metric_data
        
        # Detect patterns
        analysis['patterns'] = self._detect_patterns(data['samples'])
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _aggregate_metric(self, samples: List[Dict], metric_name: str) -> Optional[Dict]:
        """Aggregate a metric across all samples."""
        values = []
        mins = []
        maxs = []
        avgs = []
        
        for sample in samples:
            if metric_name in sample:
                m = sample[metric_name]
                if 'min' in m:
                    mins.append(m['min'])
                if 'max' in m:
                    maxs.append(m['max'])
                if 'avg' in m:
                    avgs.append(m['avg'])
        
        if not avgs:
            return None
        
        return {
            'overall_min': min(mins) if mins else None,
            'overall_max': max(maxs) if maxs else None,
            'overall_avg': statistics.mean(avgs) if avgs else None,
            'avg_min': statistics.mean(mins) if mins else None,
            'avg_max': statistics.mean(maxs) if maxs else None,
            'sample_count': len(avgs),
            'peak_times': self._identify_peak_times(samples, metric_name)
        }
    
    def _identify_peak_times(self, samples: List[Dict], metric_name: str) -> List[Dict]:
        """Identify peak usage times."""
        peaks = []
        
        for sample in samples:
            if metric_name in sample:
                m = sample[metric_name]
                if 'max' in m and m['max'] > 80:  # Threshold: 80%
                    peaks.append({
                        'time': sample.get('sample_time', 'unknown'),
                        'value': m['max']
                    })
        
        return sorted(peaks, key=lambda x: x['value'], reverse=True)[:5]
    
    def _detect_patterns(self, samples: List[Dict]) -> Dict:
        """Detect usage patterns."""
        patterns = {
            'high_usage_periods': [],
            'low_usage_periods': [],
            'anomalies': []
        }
        
        # Check for high/low usage periods
        cpu_samples = [(s.get('sample_time'), s.get('cpu', {}).get('avg', 0)) for s in samples]
        
        for time, cpu in cpu_samples:
            if cpu > 80:
                patterns['high_usage_periods'].append({'time': time, 'cpu': cpu})
            elif cpu < 10:
                patterns['low_usage_periods'].append({'time': time, 'cpu': cpu})
        
        # Detect anomalies (sudden spikes)
        cpu_values = [s.get('cpu', {}).get('avg', 0) for s in samples if 'cpu' in s]
        if len(cpu_values) >= 3:
            avg = statistics.mean(cpu_values)
            stdev = statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
            
            for i, sample in enumerate(samples):
                cpu = sample.get('cpu', {}).get('avg', 0)
                if stdev > 0 and abs(cpu - avg) > 2 * stdev:
                    patterns['anomalies'].append({
                        'time': sample.get('sample_time'),
                        'type': 'spike' if cpu > avg else 'drop',
                        'value': cpu,
                        'expected': avg
                    })
        
        return patterns
    
    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Check CPU usage
        cpu = analysis['metrics'].get('cpu', {})
        if cpu:
            avg_cpu = cpu.get('overall_avg', 0)
            max_cpu = cpu.get('overall_max', 0)
            
            if avg_cpu < 20:
                recommendations.append({
                    'type': 'cost_optimization',
                    'severity': 'high',
                    'message': f"CPU 平均使用率仅 {avg_cpu:.1f}%，建议降配以节省成本",
                    'metric': 'cpu',
                    'value': avg_cpu
                })
            elif avg_cpu > 80:
                recommendations.append({
                    'type': 'performance',
                    'severity': 'high',
                    'message': f"CPU 平均使用率高达 {avg_cpu:.1f}%，建议升级规格以提升性能",
                    'metric': 'cpu',
                    'value': avg_cpu
                })
            
            if max_cpu >= 95:
                recommendations.append({
                    'type': 'performance',
                    'severity': 'medium',
                    'message': f"CPU 峰值使用率达 {max_cpu:.1f}%，存在性能瓶颈风险",
                    'metric': 'cpu_max',
                    'value': max_cpu
                })
        
        # Check memory usage
        memory = analysis['metrics'].get('memory', {})
        if memory:
            avg_mem = memory.get('overall_avg', 0)
            max_mem = memory.get('overall_max', 0)
            
            if avg_mem < 30:
                recommendations.append({
                    'type': 'cost_optimization',
                    'severity': 'medium',
                    'message': f"内存平均使用率仅 {avg_mem:.1f}%，可考虑降低内存规格",
                    'metric': 'memory',
                    'value': avg_mem
                })
            elif max_mem >= 90:
                recommendations.append({
                    'type': 'reliability',
                    'severity': 'high',
                    'message': f"内存峰值使用率达 {max_mem:.1f}%，存在 OOM 风险",
                    'metric': 'memory_max',
                    'value': max_mem
                })
        
        # Check GPU usage
        gpu = analysis['metrics'].get('gpu', {})
        if gpu:
            avg_gpu = gpu.get('overall_avg', 0)
            
            if avg_gpu < 20:
                recommendations.append({
                    'type': 'cost_optimization',
                    'severity': 'high',
                    'message': f"GPU 平均使用率仅 {avg_gpu:.1f}%，GPU 资源利用率较低",
                    'metric': 'gpu',
                    'value': avg_gpu
                })
        
        # Check for idle periods
        patterns = analysis.get('patterns', {})
        low_usage = patterns.get('low_usage_periods', [])
        if len(low_usage) > len(analysis.get('metrics', {}).get('cpu', {}).get('sample_count', 0)) * 0.5:
            recommendations.append({
                'type': 'scheduling',
                'severity': 'medium',
                'message': "超过 50% 的时间处于低负载状态，建议配置自动停止策略",
                'metric': 'idle_ratio',
                'value': len(low_usage)
            })
        
        return recommendations
    
    def save_history(self, data: Dict, instance_id: str):
        """Save collected data to history file."""
        date_str = datetime.utcnow().strftime('%Y%m%d')
        filename = self.history_dir / f"metrics_{instance_id}_{date_str}.json"
        
        existing = []
        if filename.exists():
            with open(filename, 'r') as f:
                try:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = [existing]
                except:
                    existing = []
        
        existing.append(data)
        
        with open(filename, 'w') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        
        # Also update aggregated trend file
        trend_file = self.history_dir / f"trends_{instance_id}.json"
        self._update_trend_file(trend_file, data)
    
    def _update_trend_file(self, trend_file: Path, data: Dict):
        """Update the aggregated trend file."""
        trends = {}
        if trend_file.exists():
            with open(trend_file, 'r') as f:
                try:
                    trends = json.load(f)
                except:
                    trends = {}
        
        # Update with new data
        date_key = datetime.utcnow().strftime('%Y-%m-%d')
        if 'daily' not in trends:
            trends['daily'] = {}
        
        trends['daily'][date_key] = {
            'samples': len(data.get('samples', [])),
            'collected_at': data.get('collected_at')
        }
        trends['last_updated'] = datetime.utcnow().isoformat()
        
        with open(trend_file, 'w') as f:
            json.dump(trends, f, indent=2, ensure_ascii=False)
    
    def load_history(self, instance_id: str, days: int = 7) -> List[Dict]:
        """Load historical data for an instance."""
        history = []
        
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y%m%d')
            filename = self.history_dir / f"metrics_{instance_id}_{date}.json"
            
            if filename.exists():
                with open(filename, 'r') as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, list):
                            history.extend(data)
                        else:
                            history.append(data)
                    except:
                        pass
        
        return history
    
    def compare_periods(
        self,
        current: Dict,
        previous: Dict
    ) -> Dict:
        """Compare two analysis periods."""
        comparison = {
            'current': current['period'],
            'previous': previous['period'],
            'changes': {}
        }
        
        for metric in DEFAULT_METRICS:
            curr = current['metrics'].get(metric, {})
            prev = previous['metrics'].get(metric, {})
            
            if curr and prev:
                curr_avg = curr.get('overall_avg', 0)
                prev_avg = prev.get('overall_avg', 0)
                
                if prev_avg > 0:
                    change_pct = ((curr_avg - prev_avg) / prev_avg) * 100
                else:
                    change_pct = 0
                
                comparison['changes'][metric] = {
                    'current_avg': curr_avg,
                    'previous_avg': prev_avg,
                    'change_pct': change_pct,
                    'trend': 'increasing' if change_pct > 5 else 'decreasing' if change_pct < -5 else 'stable'
                }
        
        return comparison


def format_report_text(analysis: Dict) -> str:
    """Format analysis as readable text report."""
    lines = []
    
    lines.append("=" * 70)
    lines.append("  PAI-DSW 资源趋势分析报告")
    lines.append("=" * 70)
    
    lines.append(f"\n实例 ID: {analysis['instance_id']}")
    lines.append(f"分析时段: {analysis['period']['start']} ~ {analysis['period']['end']}")
    lines.append(f"时长: {analysis['period']['duration_hours']:.1f} 小时")
    
    # Metrics summary
    lines.append("\n" + "-" * 70)
    lines.append("  资源使用统计")
    lines.append("-" * 70)
    
    for metric, data in analysis['metrics'].items():
        metric_names = {
            'cpu': 'CPU',
            'memory': '内存',
            'gpu': 'GPU',
            'gpu-memory': 'GPU 显存'
        }
        name = metric_names.get(metric, metric)
        
        lines.append(f"\n{name}:")
        lines.append(f"  平均: {data['overall_avg']:.1f}%")
        lines.append(f"  最小: {data['overall_min']:.1f}%")
        lines.append(f"  最大: {data['overall_max']:.1f}%")
        lines.append(f"  样本数: {data['sample_count']}")
        
        if data['peak_times']:
            lines.append(f"  峰值时刻:")
            for peak in data['peak_times'][:3]:
                lines.append(f"    - {peak['time']}: {peak['value']:.1f}%")
    
    # Patterns
    patterns = analysis['patterns']
    lines.append("\n" + "-" * 70)
    lines.append("  使用模式分析")
    lines.append("-" * 70)
    
    if patterns['high_usage_periods']:
        lines.append(f"\n高负载时段: {len(patterns['high_usage_periods'])} 次")
    if patterns['low_usage_periods']:
        lines.append(f"低负载时段: {len(patterns['low_usage_periods'])} 次")
    if patterns['anomalies']:
        lines.append(f"异常波动: {len(patterns['anomalies'])} 次")
        for anomaly in patterns['anomalies'][:5]:
            lines.append(f"  - {anomaly['time']}: {anomaly['type']} ({anomaly['value']:.1f}%)")
    
    # Recommendations
    if analysis['recommendations']:
        lines.append("\n" + "-" * 70)
        lines.append("  优化建议")
        lines.append("-" * 70)
        
        for rec in analysis['recommendations']:
            severity_icons = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
            icon = severity_icons.get(rec['severity'], '⚪')
            lines.append(f"\n{icon} [{rec['type']}] {rec['message']}")
    
    lines.append("\n" + "=" * 70)
    
    return "\n".join(lines)


def format_report_json(analysis: Dict) -> str:
    """Format analysis as JSON."""
    return json.dumps(analysis, indent=2, ensure_ascii=False)


def format_report_csv(analysis: Dict) -> str:
    """Format analysis as CSV."""
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['metric', 'avg', 'min', 'max', 'sample_count'])
    
    # Data rows
    for metric, data in analysis['metrics'].items():
        writer.writerow([
            metric,
            f"{data['overall_avg']:.2f}",
            f"{data['overall_min']:.2f}",
            f"{data['overall_max']:.2f}",
            data['sample_count']
        ])
    
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(
        description='Analyze PAI-DSW resource usage trends',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析当前实例过去 7 天的资源趋势
  python analyze_trends.py --days 7

  # 分析指定实例
  python analyze_trends.py --instance dsw-123456 --days 3

  # 分析所有实例并保存数据
  python analyze_trends.py --all --days 7 --save

  # 生成 CSV 格式报告
  python analyze_trends.py --instance dsw-123456 --days 7 --format csv

  # 与上一周对比
  python analyze_trends.py --days 7 --compare

输出说明:
  - overall_avg: 整个时段的平均值
  - overall_min/max: 最小/最大值
  - peak_times: 峰值使用时段
  - patterns: 使用模式（高/低负载、异常）
  - recommendations: 优化建议
"""
    )
    
    parser.add_argument('--instance', help='实例 ID（不指定则使用当前实例）')
    parser.add_argument('--instances', help='逗号分隔的实例 ID 列表')
    parser.add_argument('--all', action='store_true', help='分析所有实例')
    parser.add_argument('--days', type=int, default=7, help='分析天数（默认: 7）')
    parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--interval', type=int, default=1, help='采集间隔（小时，默认: 1）')
    parser.add_argument('--save', action='store_true', help='保存采集数据到历史文件')
    parser.add_argument('--load', action='store_true', help='从历史文件加载数据')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--format', '-f', choices=['text', 'json', 'csv'], default='text',
                        help='输出格式（默认: text）')
    parser.add_argument('--compare', action='store_true', help='与上一周期对比')
    
    args = parser.parse_args()
    
    try:
        analyzer = TrendAnalyzer()
        
        # Determine instance IDs
        instance_ids = []
        if args.instance:
            instance_ids = [args.instance]
        elif args.instances:
            instance_ids = [i.strip() for i in args.instances.split(',')]
        elif args.all:
            # List all instances
            from list_instances import list_instances
            instances = list_instances()
            instance_ids = [i['InstanceId'] for i in instances]
        else:
            # Use current instance
            instance_ids = [get_current_instance_id()]
        
        if not instance_ids:
            print("错误: 未找到要分析的实例", file=sys.stderr)
            sys.exit(1)
        
        # Determine time range
        if args.end:
            end_time = datetime.strptime(args.end, '%Y-%m-%d')
        else:
            end_time = datetime.utcnow()
        
        if args.start:
            start_time = datetime.strptime(args.start, '%Y-%m-%d')
        else:
            start_time = end_time - timedelta(days=args.days)
        
        results = []
        
        for instance_id in instance_ids:
            print(f"正在分析实例: {instance_id}...", file=sys.stderr)
            
            if args.load:
                # Load from history
                history = analyzer.load_history(instance_id, args.days)
                if history:
                    data = {'samples': [], 'instance_id': instance_id}
                    for h in history:
                        data['samples'].extend(h.get('samples', []))
                else:
                    print(f"警告: 未找到实例 {instance_id} 的历史数据", file=sys.stderr)
                    continue
            else:
                # Collect fresh data
                data = analyzer.collect_metrics(
                    instance_id,
                    start_time,
                    end_time,
                    args.interval
                )
            
            # Analyze
            analysis = analyzer.analyze_trends(data)
            
            # Compare with previous period if requested
            if args.compare:
                prev_start = start_time - timedelta(days=args.days)
                prev_end = start_time
                prev_data = analyzer.collect_metrics(
                    instance_id,
                    prev_start,
                    prev_end,
                    args.interval
                )
                prev_analysis = analyzer.analyze_trends(prev_data)
                analysis['comparison'] = analyzer.compare_periods(analysis, prev_analysis)
            
            # Save if requested
            if args.save:
                analyzer.save_history(data, instance_id)
                print(f"数据已保存到: {HISTORY_DIR}", file=sys.stderr)
            
            results.append(analysis)
        
        # Format output
        if args.format == 'json':
            output = json.dumps(results, indent=2, ensure_ascii=False)
        elif args.format == 'csv':
            output = "\n".join(format_report_csv(r) for r in results)
        else:
            output = "\n\n".join(format_report_text(r) for r in results)
        
        # Write output
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"报告已保存到: {args.output}", file=sys.stderr)
        else:
            print(output)
    
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()