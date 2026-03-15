/**
 * Library Page - Unified Library with Timelines and Skeletons
 *
 * Two-column card grid with URL-driven tabs, shared filter controls.
 */

import { useNavigate, useSearchParams } from 'react-router-dom';
import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { importTimeline, getTimelines, deleteTimeline, getSkeletons, deleteSkeleton, generateFromSkeleton } from '../services/api';
import { LibraryControlsHeader } from '../components/LibraryControlsHeader';
import { CompactTimelineCard } from '../components/CompactTimelineCard';
import { CompactSkeletonCard } from '../components/CompactSkeletonCard';
import type { TimelineListItem, ScenarioType, Skeleton } from '../types';

type TabType = 'timelines' | 'skeletons';

const QUERY_KEYS = {
  TAB: 'tab',
  SEARCH: 'search',
  SCENARIO_FILTER: 'scenario',
  SORT: 'sort'
} as const;

const LibraryPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getInitialTab = (): TabType => (searchParams.get(QUERY_KEYS.TAB) === 'skeletons' ? 'skeletons' : 'timelines');

  const [activeTab, setActiveTab] = useState<TabType>(getInitialTab);
  const [timelines, setTimelines] = useState<TimelineListItem[]>([]);
  const [skeletons, setSkeletons] = useState<Skeleton[]>([]);
  const [loading, setLoading] = useState({ timelines: true, skeletons: true });
  const [error, setError] = useState<{ timelines: string | null; skeletons: string | null }>({ timelines: null, skeletons: null });
  const [isImporting, setIsImporting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [generatingFromSkeleton, setGeneratingFromSkeleton] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState(searchParams.get(QUERY_KEYS.SEARCH) || '');
  const [scenarioFilter, setScenarioFilter] = useState<ScenarioType | 'all'>((searchParams.get(QUERY_KEYS.SCENARIO_FILTER) as ScenarioType | 'all') || 'all');
  const [sortBy, setSortBy] = useState<'date_created' | 'name'>((searchParams.get(QUERY_KEYS.SORT) as 'date_created' | 'name') || 'date_created');

  const updateSearchParams = useCallback((updates: Partial<Record<typeof QUERY_KEYS[keyof typeof QUERY_KEYS], string>>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) newParams.set(key, value); else newParams.delete(key);
    });
    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);

  const handleTabChange = useCallback((tab: TabType) => {
    setActiveTab(tab);
    updateSearchParams({ [QUERY_KEYS.TAB]: tab });
  }, [updateSearchParams]);

  const handleSearchChange = useCallback((query: string) => {
    setSearchQuery(query);
    updateSearchParams({ [QUERY_KEYS.SEARCH]: query });
  }, [updateSearchParams]);

  const handleScenarioFilterChange = useCallback((filter: ScenarioType | 'all') => {
    setScenarioFilter(filter);
    updateSearchParams({ [QUERY_KEYS.SCENARIO_FILTER]: filter });
  }, [updateSearchParams]);

  const handleSortByChange = useCallback((sort: 'date_created' | 'name') => {
    setSortBy(sort);
    updateSearchParams({ [QUERY_KEYS.SORT]: sort });
  }, [updateSearchParams]);

  useEffect(() => {
    const tabParam = searchParams.get(QUERY_KEYS.TAB);
    const newTab = (tabParam === 'skeletons' ? 'skeletons' : 'timelines');
    if (newTab !== activeTab) setActiveTab(newTab);

    const searchParam = searchParams.get(QUERY_KEYS.SEARCH) || '';
    if (searchParam !== searchQuery) setSearchQuery(searchParam);

    const scenarioParam = (searchParams.get(QUERY_KEYS.SCENARIO_FILTER) as ScenarioType | 'all') || 'all';
    if (scenarioParam !== scenarioFilter) setScenarioFilter(scenarioParam);

    const sortParam = (searchParams.get(QUERY_KEYS.SORT) as 'date_created' | 'name') || 'date_created';
    if (sortParam !== sortBy) setSortBy(sortParam);
  }, [searchParams, activeTab, searchQuery, scenarioFilter, sortBy]);

  useEffect(() => {
    const fetchTimelines = async () => {
      try {
        setLoading(prev => ({ ...prev, timelines: true }));
        const response = await getTimelines();
        if (response.error) {
          setError(prev => ({ ...prev, timelines: response.error?.message || 'Failed to load timelines' }));
        } else if (response.data) {
          setTimelines(response.data);
          setError(prev => ({ ...prev, timelines: null }));
        }
      } catch {
        setError(prev => ({ ...prev, timelines: 'An unexpected error occurred' }));
      } finally {
        setLoading(prev => ({ ...prev, timelines: false }));
      }
    };
    fetchTimelines();
  }, []);

  useEffect(() => {
    const fetchSkeletons = async () => {
      try {
        setLoading(prev => ({ ...prev, skeletons: true }));
        const response = await getSkeletons();
        if (response.error) {
          setError(prev => ({ ...prev, skeletons: response.error?.message || 'Failed to load skeletons' }));
        } else if (response.data) {
          setSkeletons(response.data);
          setError(prev => ({ ...prev, skeletons: null }));
        }
      } catch {
        setError(prev => ({ ...prev, skeletons: 'An unexpected error occurred' }));
      } finally {
        setLoading(prev => ({ ...prev, skeletons: false }));
      }
    };
    fetchSkeletons();
  }, []);

  const filteredAndSortedTimelines = useMemo(() => {
    let result = timelines;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(t => t.timeline_name?.toLowerCase().includes(q) || t.root_deviation_description.toLowerCase().includes(q));
    }
    if (scenarioFilter !== 'all') result = result.filter(t => t.scenario_type === scenarioFilter);
    return [...result].sort((a, b) => {
      if (sortBy === 'date_created') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      const na = a.timeline_name || a.root_deviation_description;
      const nb = b.timeline_name || b.root_deviation_description;
      return na.localeCompare(nb);
    });
  }, [timelines, searchQuery, scenarioFilter, sortBy]);

  const filteredAndSortedSkeletons = useMemo(() => {
    let result = skeletons;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(s => s.deviation_description?.toLowerCase().includes(q) || s.events.some(e => e.description.toLowerCase().includes(q)));
    }
    if (scenarioFilter !== 'all') result = result.filter(s => s.skeleton_type === 'timeline_draft' && s.scenario_type === scenarioFilter);
    return [...result].sort((a, b) => {
      if (sortBy === 'date_created') return new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime();
      const na = a.deviation_description || 'Unnamed Skeleton';
      const nb = b.deviation_description || 'Unnamed Skeleton';
      return na.localeCompare(nb);
    });
  }, [skeletons, searchQuery, scenarioFilter, sortBy]);

  const handleCreateNew = () => navigate('/console');
  const handleImportClick = () => fileInputRef.current?.click();
  const handleTimelineClick = (timelineId: string) => navigate(`/reports/${timelineId}`);
  const handleSkeletonClick = (skeletonId: string) => navigate(`/skeleton-workflow?id=${skeletonId}`);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.devtl')) { alert('Invalid file type. Please select a .devtl file.'); return; }
    setIsImporting(true);
    try {
      const response = await importTimeline(file);
      if (response.error) { alert(`Import failed: ${response.error.message}`); }
      else if (response.data) { alert('Timeline imported successfully!'); navigate(`/reports/${response.data.id}`); }
    } catch { alert('An unexpected error occurred during import.'); }
    finally { setIsImporting(false); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  const handleDeleteTimeline = async (timelineId: string) => {
    if (!confirm('Are you sure you want to delete this timeline? This action cannot be undone.')) return;
    setDeletingId(timelineId);
    try {
      const response = await deleteTimeline(timelineId);
      if (response.error) setError(prev => ({ ...prev, timelines: `Failed to delete: ${response.error?.message}` }));
      else setTimelines(prev => prev.filter(t => t.id !== timelineId));
    } catch { setError(prev => ({ ...prev, timelines: 'Failed to delete timeline' })); }
    finally { setDeletingId(null); }
  };

  const handleDeleteSkeleton = async (skeletonId: string) => {
    if (!confirm('Are you sure you want to delete this skeleton? This action cannot be undone.')) return;
    setDeletingId(skeletonId);
    try {
      const response = await deleteSkeleton(skeletonId);
      if (response.error) setError(prev => ({ ...prev, skeletons: `Failed to delete: ${response.error?.message}` }));
      else setSkeletons(prev => prev.filter(s => s.id !== skeletonId));
    } catch { setError(prev => ({ ...prev, skeletons: 'Failed to delete skeleton' })); }
    finally { setDeletingId(null); }
  };

  const handleGenerateFromSkeleton = async (skeletonId: string) => {
    if (!confirm('Generate a timeline report from this skeleton?')) return;
    setGeneratingFromSkeleton(skeletonId);
    try {
      const response = await generateFromSkeleton({ skeleton_id: skeletonId });
      if (response.error) { alert(`Failed to generate timeline: ${response.error?.message}`); }
      else if (response.data) { alert('Timeline generated successfully!'); navigate(`/reports/${response.data.id}`); }
    } catch { alert('An unexpected error occurred during generation.'); }
    finally { setGeneratingFromSkeleton(null); }
  };

  const tabs = [
    { id: 'timelines' as TabType, label: 'Timelines', count: filteredAndSortedTimelines.length },
    { id: 'skeletons' as TabType, label: 'Skeletons', count: filteredAndSortedSkeletons.length },
  ];

  const isLoading = loading[activeTab];
  const currentError = error[activeTab];
  const currentData = activeTab === 'timelines' ? filteredAndSortedTimelines : filteredAndSortedSkeletons;

  const handleTabKeyDown = (event: React.KeyboardEvent, tabId: TabType) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); handleTabChange(tabId); }
  };

  return (
    <div className="min-h-screen bg-vellum">
      <LibraryControlsHeader
        onCreateNew={handleCreateNew}
        onImport={handleImportClick}
        isImporting={isImporting}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        scenarioFilter={scenarioFilter}
        onScenarioFilterChange={handleScenarioFilterChange}
        sortBy={sortBy}
        onSortByChange={handleSortByChange}
      />

      <input ref={fileInputRef} type="file" accept=".devtl" onChange={handleFileSelect} className="hidden" />

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-6 pt-5">
        <nav className="flex gap-0 border-b border-border" role="tablist" aria-label="Library sections">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`panel-${tab.id}`}
              tabIndex={activeTab === tab.id ? 0 : -1}
              onClick={() => handleTabChange(tab.id)}
              onKeyDown={(e) => handleTabKeyDown(e, tab.id)}
              className={`px-5 py-2.5 font-mono text-[9px] tracking-widest uppercase border-b-2 transition-all -mb-px ${
                activeTab === tab.id
                  ? 'border-gold text-gold'
                  : 'border-transparent text-faint hover:text-dim hover:border-gold-dim'
              }`}
            >
              {tab.label}
              {tab.count > 0 && (
                <span className={`ml-2 font-mono text-[9px] ${activeTab === tab.id ? 'text-gold-dim' : 'text-faint'}`}>
                  ({tab.count})
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div id={`panel-${activeTab}`} role="tabpanel" aria-labelledby={`tab-${activeTab}`}>
          {isLoading ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="text-center space-y-3">
                <div className="inline-block w-10 h-10 border border-gold border-t-transparent rounded-full animate-spin" />
                <p className="font-mono text-[9px] tracking-widest uppercase text-dim">Loading {activeTab}...</p>
              </div>
            </div>
          ) : currentError ? (
            <div className="border border-rubric/40 bg-rubric/5 p-6 corner-brackets">
              <h3 className="font-mono text-[9px] tracking-widest uppercase text-rubric mb-2">Error</h3>
              <p className="font-body text-sm text-dim mb-4">{currentError}</p>
              <button
                onClick={() => window.location.reload()}
                className="font-mono text-[9px] tracking-widest uppercase border border-rubric/50 text-rubric px-3 py-1.5 hover:bg-rubric/10 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : currentData.length === 0 ? (
            <div className="text-center py-20">
              <p className="font-display text-2xl text-ink mb-3">
                {searchQuery || scenarioFilter !== 'all'
                  ? `No Matching ${activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}`
                  : `No ${activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Yet`}
              </p>
              <p className="font-body text-sm text-dim mb-8 max-w-sm mx-auto">
                {searchQuery || scenarioFilter !== 'all'
                  ? 'Try adjusting your search or filter criteria.'
                  : activeTab === 'timelines'
                  ? 'Create your first alternate history timeline to get started.'
                  : 'Create your first skeleton timeline from the Deviation Console.'}
              </p>
              {!searchQuery && scenarioFilter === 'all' && (
                <button
                  onClick={handleCreateNew}
                  className="font-mono text-[10px] tracking-widest uppercase border border-gold text-gold px-5 py-2.5 hover:bg-gold/10 hover:shadow-[var(--shadow-gold)] transition-all"
                >
                  {activeTab === 'timelines' ? 'Create First Timeline' : 'Go to Console'}
                </button>
              )}
            </div>
          ) : (
            /* Two-column grid */
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {activeTab === 'timelines'
                ? filteredAndSortedTimelines.map(timeline => (
                    <CompactTimelineCard
                      key={timeline.id}
                      timeline={timeline}
                      onClick={() => handleTimelineClick(timeline.id)}
                      onDelete={() => handleDeleteTimeline(timeline.id)}
                      isDeleting={deletingId === timeline.id}
                    />
                  ))
                : filteredAndSortedSkeletons.map(skeleton => (
                    <CompactSkeletonCard
                      key={skeleton.id}
                      skeleton={skeleton}
                      onClick={() => handleSkeletonClick(skeleton.id)}
                      onDelete={() => handleDeleteSkeleton(skeleton.id)}
                      onGenerate={() => handleGenerateFromSkeleton(skeleton.id)}
                      isDeleting={deletingId === skeleton.id}
                      isGenerating={generatingFromSkeleton === skeleton.id}
                    />
                  ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LibraryPage;
