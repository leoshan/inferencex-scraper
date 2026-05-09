import ReactECharts from 'echarts-for-react'

interface DistributionPieProps {
  data: Record<string, number>
  title?: string
  height?: number
}

export default function DistributionPie({ data, title, height = 400 }: DistributionPieProps) {
  const chartData = Object.entries(data)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10)

  const option = {
    title: { text: title, left: 'center' },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => `${params.name}: ${(params.value / 1e9).toFixed(2)}B (${params.percent}%)`,
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 10,
      top: 60,
      bottom: 20,
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '55%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: false,
          position: 'center',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
          },
        },
        labelLine: { show: false },
        data: chartData,
      },
    ],
  }

  return <ReactECharts option={option} style={{ height }} />
}
