export type UserRole = 'admin' | 'instructor' | 'student'

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: UserRole
  organization_id: string
  is_active: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  settings: Record<string, unknown>
  is_active: boolean
  created_at: string
}

export interface Course {
  id: string
  organization_id: string
  name: string
  description: string | null
  semester: string | null
  year: number | null
  is_active: boolean
  instructor_id: string
  created_at: string
  updated_at: string
}

export interface EnrollmentResponse {
  id: string
  user_id: string
  course_id: string
  status: string
  created_at: string
}

export type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical'
export type IncidentStatus = 'open' | 'investigating' | 'contained' | 'resolved' | 'closed'

export interface Incident {
  id: string
  organization_id: string
  incident_number: string
  title: string
  description: string | null
  severity: IncidentSeverity
  status: IncidentStatus
  category: string | null
  assigned_to: string | null
  team_id: string | null
  detected_at: string | null
  contained_at: string | null
  resolved_at: string | null
  closed_at: string | null
  created_at: string
  updated_at: string
}

export interface Alert {
  id: string
  organization_id: string
  wazuh_alert_id: string | null
  is_simulated: boolean
  rule_id: number | null
  rule_level: number | null
  rule_description: string | null
  rule_groups: string[]
  agent_id: string | null
  agent_name: string | null
  endpoint_id: string | null
  raw_data: Record<string, unknown>
  timestamp: string
  is_acknowledged: boolean
  acknowledged_by: string | null
  acknowledged_at: string | null
  created_at: string
}

export interface IncidentAlert {
  id: string
  incident_id: string
  alert_id: string
  created_at: string
}

export interface Evidence {
  id: string
  incident_id: string
  submitted_by: string
  evidence_type: string
  title: string
  description: string | null
  artifact: string | null
  created_at: string
  updated_at: string
}

export interface CaseNote {
  id: string
  incident_id: string
  author_id: string
  content: string
  created_at: string
  updated_at: string
}

export interface StudentDecision {
  id: string
  incident_id: string
  student_id: string
  decision_type: string
  title: string
  rationale: string | null
  occurred_at: string
  created_at: string
}

export type ScenarioDifficulty = 'beginner' | 'intermediate' | 'advanced' | 'expert'
export type ScenarioRunStatus = 'active' | 'completed' | 'aborted'
export type InjectType = 'alert' | 'email' | 'chat' | 'phone' | 'file' | 'custom'
export type InjectStatus = 'pending' | 'fired' | 'failed' | 'skipped'

export interface Scenario {
  id: string
  slug: string
  name: string
  version: string
  difficulty: ScenarioDifficulty
  estimated_duration_minutes: number | null
  description: string | null
  objectives: unknown[]
  ttps: unknown[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ScenarioRun {
  id: string
  scenario_id: string
  course_id: string
  team_id: string | null
  incident_id: string | null
  started_by: string
  status: ScenarioRunStatus
  started_at: string | null
  completed_at: string | null
  settings: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface Inject {
  id: string
  scenario_run_id: string
  inject_slug: string
  inject_type: InjectType
  scheduled_at: string
  fired_at: string | null
  status: InjectStatus
  result: Record<string, unknown> | null
  error_message: string | null
}

export type CampaignRunStatus = 'draft' | 'active' | 'completed' | 'aborted'
export type CampaignProgressStatus = 'pending' | 'active' | 'completed' | 'skipped'

export interface Campaign {
  id: string
  slug: string
  name: string
  description: string | null
  is_active: boolean
  created_by: string
  created_at: string
  updated_at: string
}

export interface CampaignScenarioEntry {
  id: string
  campaign_id: string
  scenario_id: string
  order_index: number
  day_offset: number
  is_optional: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface CampaignRun {
  id: string
  campaign_id: string
  course_id: string
  team_id: string | null
  started_by: string
  status: CampaignRunStatus
  started_at: string | null
  completed_at: string | null
  settings: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface CampaignRunProgress {
  id: string
  campaign_run_id: string
  campaign_scenario_entry_id: string
  scenario_run_id: string | null
  order_index: number
  status: CampaignProgressStatus
  created_at: string
  updated_at: string
}

export interface CampaignRunScenarioSummary {
  order_index: number
  campaign_scenario_entry_id: string
  scenario_id: string
  scenario_name: string
  scenario_slug: string
  is_optional: boolean
  progress_status: string
  scenario_run_id: string | null
  scenario_run_status: string | null
  decisions_count: number
}

export interface CampaignRunReport {
  campaign_run_id: string
  campaign_name: string
  campaign_slug: string
  status: string
  course_id: string
  started_at: string | null
  completed_at: string | null
  scenarios_total: number
  scenarios_completed: number
  scenarios_pending: number
  scenarios_skipped: number
  total_decisions: number
  scenarios: CampaignRunScenarioSummary[]
}

export interface GradeResponse {
  id: string
  scenario_run_id: string
  course_id: string
  student_id: string
  graded_by: string
  score: number
  max_score: number
  rubric: Record<string, unknown>
  feedback: string | null
  graded_at: string
  created_at: string
  updated_at: string
}

export interface InjectStats {
  total: number
  fired: number
  pending: number
  skipped: number
  failed: number
}

export interface DecisionStats {
  total: number
  by_type: Record<string, number>
}

export interface TimelineEvent {
  event_type: 'inject' | 'decision'
  occurred_at: string
  title: string
  detail: Record<string, unknown>
}

export interface ScenarioRunReport {
  run_id: string
  scenario_slug: string
  scenario_name: string
  difficulty: string
  status: string
  started_at: string | null
  completed_at: string | null
  duration_minutes: number | null
  injects: InjectStats
  decisions: DecisionStats
  timeline: TimelineEvent[]
  grades: GradeResponse[]
}

export interface CourseLeaderboardEntry {
  student_id: string
  student_name: string
  student_email: string
  runs_graded: number
  average_score: number
  highest_score: number
  total_decisions: number
}
