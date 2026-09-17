import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { teamsAPI } from '../lib/api';

const TeamContext = createContext(null);

export const TeamProvider = ({ children }) => {
  const { user } = useAuth();
  
  const [teams, setTeams] = useState([]);
  const [activeTeam, setActiveTeam] = useState(null);
  const [activeTeamId, setActiveTeamId] = useState(() => {
    const saved = localStorage.getItem('socialpilot_active_team_id');
    return saved ? parseInt(saved, 10) : null;
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTeamsList = useCallback(async (silent = false) => {
    if (!user) {
      setTeams([]);
      setActiveTeam(null);
      setActiveTeamId(null);
      setIsLoading(false);
      return;
    }

    if (!silent) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const res = await teamsAPI.list();
      const list = res.data || [];
      setTeams(list);

      if (list.length === 0) {
        setActiveTeam(null);
        setActiveTeamId(null);
        localStorage.removeItem('socialpilot_active_team_id');
      } else {
        // Find stored active team or fallback to first team
        const savedId = localStorage.getItem('socialpilot_active_team_id');
        const parsedSavedId = savedId ? parseInt(savedId, 10) : null;
        
        const matchingTeam = list.find((t) => t.id === parsedSavedId);
        if (matchingTeam) {
          setActiveTeam(matchingTeam);
          setActiveTeamId(matchingTeam.id);
        } else {
          setActiveTeam(list[0]);
          setActiveTeamId(list[0].id);
          localStorage.setItem('socialpilot_active_team_id', list[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load user teams:', err);
      const d = err.response?.data?.detail;
      setError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Failed to retrieve workspaces.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  // Load teams on mount or when user shifts
  useEffect(() => {
    fetchTeamsList();
  }, [fetchTeamsList]);

  // Switch team function
  const switchTeam = useCallback((teamId) => {
    if (!teamId) {
      setActiveTeam(null);
      setActiveTeamId(null);
      localStorage.removeItem('socialpilot_active_team_id');
      return;
    }

    const matching = teams.find((t) => t.id === teamId);
    if (matching) {
      setActiveTeam(matching);
      setActiveTeamId(matching.id);
      localStorage.setItem('socialpilot_active_team_id', matching.id);
    }
  }, [teams]);

  const value = {
    teams,
    activeTeam,
    activeTeamId,
    isLoading,
    error,
    switchTeam,
    refreshTeams: () => fetchTeamsList(true),
  };

  return <TeamContext.Provider value={value}>{children}</TeamContext.Provider>;
};

export const useTeam = () => {
  const context = useContext(TeamContext);
  if (!context) {
    throw new Error('useTeam must be used within a TeamProvider');
  }
  return context;
};
