import { Typography, Row, Col, Card, Statistic } from 'antd'
import { ProjectOutlined, ExperimentOutlined, CheckCircleOutlined } from '@ant-design/icons'

const { Title } = Typography

function DashboardPage() {
  return (
    <div>
      <Title level={2}>Dashboard</Title>
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Projects"
              value={0}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Runs"
              value={0}
              prefix={<ExperimentOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Completed Runs"
              value={0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>
      <Card style={{ marginTop: 24 }}>
        <Title level={4}>Recent Activity</Title>
        <p>No recent activity</p>
      </Card>
    </div>
  )
}

export default DashboardPage
