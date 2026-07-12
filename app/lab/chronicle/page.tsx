'use client';

import { useState } from 'react';
import { MQPanel, MQSearch, MQButton, MQChartContainer, MQStatusBadge } from '@/components/mqds';
import { ResearchTimeline } from '@/components/lab/ResearchTimeline';
import { TimelineInspector } from '@/components/lab/TimelineInspector';
import { mockResearchJourneys, TimelineEvent, getAllEvents } from '@/lib/mock-data/chronicle';
import { Filter, BookOpen } from 'lucide-react';

export default function ChroniclePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [journeyFilter, setJourneyFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(null);

  const filteredJourneys = mockResearchJourneys.filter(journey => {
    const matchesSearch = journey.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         journey.researcher.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         journey.journeyId.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || journey.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const selectedJourney = journeyFilter === 'ALL'
    ? null
    : mockResearchJourneys.find(j => j.journeyId === journeyFilter) || null;

  const displayJourneys = journeyFilter === 'ALL' ? filteredJourneys : (selectedJourney ? [selectedJourney] : []);

  const allEvents = getAllEvents();
  const statusCounts = mockResearchJourneys.reduce((acc, j) => {
    acc[j.status] = (acc[j.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const journeyStatusMap: Record<string, 'success' | 'failure' | 'warning' | 'running' | 'pending'> = {
    COMPLETED: 'success',
    FAILED: 'failure',
    IN_PROGRESS: 'running',
    PAUSED: 'warning'
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <MQSearch
            value={searchQuery}
            onSearch={setSearchQuery}
            placeholder="Search research journeys..."
            className="w-[300px]"
          />
          <Filter size={16} className="text-[var(--color-mq-text-secondary)]" />

          <select
            value={journeyFilter}
            onChange={(e) => setJourneyFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Journeys ({mockResearchJourneys.length})</option>
            {mockResearchJourneys.map(journey => (
              <option key={journey.journeyId} value={journey.journeyId}>
                {journey.title}
              </option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--color-mq-bg-secondary)] border border-[var(--color-mq-border)] rounded-[var(--radius-minimal)] px-2 h-8 text-[var(--font-size-small)] text-[var(--color-mq-text-primary)] font-mono"
          >
            <option value="ALL">All Status ({mockResearchJourneys.length})</option>
            <option value="COMPLETED">Completed ({statusCounts.COMPLETED || 0})</option>
            <option value="IN_PROGRESS">In Progress ({statusCounts.IN_PROGRESS || 0})</option>
            <option value="FAILED">Failed ({statusCounts.FAILED || 0})</option>
            <option value="PAUSED">Paused ({statusCounts.PAUSED || 0})</option>
          </select>
        </div>
        <MQButton>
          Export Chronicle
        </MQButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <MQChartContainer title="Total Journeys" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <BookOpen size={32} className="text-[var(--color-mq-accent)]" />
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {mockResearchJourneys.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Research Journeys
              </div>
            </div>
          </div>
        </MQChartContainer>

        <MQChartContainer title="Total Events" className="lg:col-span-1">
          <div className="h-[120px] flex flex-col justify-center items-center gap-2">
            <div className="text-center">
              <div className="text-[var(--font-size-h3)] font-mono text-[var(--color-mq-text-primary)]">
                {allEvents.length}
              </div>
              <div className="text-[var(--font-size-caption)] text-[var(--color-mq-text-secondary)]">
                Timeline Events
              </div>
            </div>
          </div>
        </MQChartContainer>

        <MQChartContainer title="Journey Status" className="lg:col-span-2">
          <div className="h-[120px] flex items-center justify-center gap-4">
            <div className="flex items-center gap-2">
              <MQStatusBadge status="success" label="COMPLETED" />
              <span className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                {statusCounts.COMPLETED || 0}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <MQStatusBadge status="running" label="IN_PROGRESS" />
              <span className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                {statusCounts.IN_PROGRESS || 0}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <MQStatusBadge status="failure" label="FAILED" />
              <span className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                {statusCounts.FAILED || 0}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <MQStatusBadge status="warning" label="PAUSED" />
              <span className="text-[var(--font-size-body)] font-mono text-[var(--color-mq-text-primary)]">
                {statusCounts.PAUSED || 0}
              </span>
            </div>
          </div>
        </MQChartContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-4">
          {displayJourneys.length === 0 ? (
            <MQPanel title="Research Journeys">
              <div className="h-[400px] flex items-center justify-center">
                <div className="text-center">
                  <BookOpen size={48} className="mx-auto mb-3 text-[var(--color-mq-text-muted)]" />
                  <div className="text-[var(--font-size-body)] text-[var(--color-mq-text-secondary)] font-mono">
                    No journeys found
                  </div>
                </div>
              </div>
            </MQPanel>
          ) : (
            displayJourneys.map(journey => (
              <MQPanel key={journey.journeyId} title={`Journey: ${journey.journeyId}`}>
                <ResearchTimeline
                  journey={journey}
                  onEventSelect={setSelectedEvent}
                  selectedEventId={selectedEvent?.id}
                />
              </MQPanel>
            ))
          )}
        </div>

        <div className="lg:sticky lg:top-4 lg:self-start">
          <TimelineInspector event={selectedEvent} />
        </div>
      </div>
    </div>
  );
}
