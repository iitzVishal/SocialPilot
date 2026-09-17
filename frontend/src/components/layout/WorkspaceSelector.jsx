import React, { useState, useEffect, useRef, useId } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTeam } from '../../context/TeamContext';
import { ChevronDown, Check, Plus, Users, Loader2 } from 'lucide-react';

export const WorkspaceSelector = () => {
  const navigate = useNavigate();
  const listboxId = useId();
  const { teams, activeTeam, activeTeamId, switchTeam, isLoading } = useTeam();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  const handleToggle = () => setIsOpen(!isOpen);

  const handleSelect = (teamId) => {
    switchTeam(teamId);
    setIsOpen(false);
  };

  const handleNavigateToTeams = () => {
    navigate('/dashboard/teams');
    setIsOpen(false);
  };

  // Keyboard navigation helpers
  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
    } else if (e.key === 'ArrowDown' && !isOpen) {
      setIsOpen(true);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200/80 dark:border-slate-800/50 bg-slate-50/50 dark:bg-[#0D1426]/30 text-slate-400 dark:text-slate-500 text-xs">
        <Loader2 className="h-3 w-3 animate-spin text-violet-500" />
        <span>Loading...</span>
      </div>
    );
  }

  return (
    <div className="relative" ref={dropdownRef} onKeyDown={handleKeyDown}>
      {/* Trigger Button */}
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-label="Select active team workspace"
        onClick={handleToggle}
        className="sp-card flex items-center gap-2.5 px-3 py-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 transition-all cursor-pointer shadow-xs select-none"
      >
        <div className="flex h-5.5 w-5.5 items-center justify-center rounded-lg bg-gradient-to-tr from-emerald-500 to-teal-500 text-white font-extrabold text-[10px] shadow-sm shadow-emerald-500/10">
          {activeTeam ? activeTeam.name.charAt(0).toUpperCase() : 'W'}
        </div>
        <span className="text-xs font-bold truncate max-w-[90px] sm:max-w-[130px]">
          {activeTeam ? activeTeam.name : 'Workspace Overview'}
        </span>
        <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Card */}
      {isOpen && (
        <div
          id={listboxId}
          role="listbox"
          aria-label="Available workspaces"
          className="sp-card absolute left-0 mt-2 w-56 p-1.5 shadow-2xl z-50 animate-sp-fade-in-up focus:outline-none"
        >
          {teams.length === 0 ? (
            <div className="px-3 py-2.5 text-center space-y-1.5">
              <p className="text-[11px] font-semibold text-slate-400 dark:text-slate-550 leading-normal">
                You do not have any workspaces.
              </p>
              <button
                type="button"
                onClick={handleNavigateToTeams}
                className="w-full inline-flex items-center justify-center gap-1.5 py-1 px-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-[10px] font-bold transition-colors cursor-pointer"
              >
                <Plus className="h-3 w-3" />
                Create Workspace
              </button>
            </div>
          ) : (
            <div className="space-y-1">
              <div className="px-2.5 py-1 text-[9px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                Switch Workspace
              </div>
              <div className="max-h-52 overflow-y-auto space-y-0.5 pr-0.5">
                {teams.map((team) => {
                  const isActive = team.id === activeTeamId;
                  return (
                    <button
                      key={team.id}
                      role="option"
                      aria-selected={isActive}
                      type="button"
                      onClick={() => handleSelect(team.id)}
                      className={`w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded-xl text-left text-xs transition-all cursor-pointer ${
                        isActive
                          ? 'bg-violet-600 text-white font-bold'
                          : 'text-slate-650 dark:text-slate-300 hover:bg-slate-100/60 dark:hover:bg-slate-800/40 hover:text-slate-900 dark:hover:text-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <div className={`flex h-5 w-5 items-center justify-center rounded bg-gradient-to-tr font-bold text-[9px] ${
                          isActive
                            ? 'from-white/20 to-white/10 text-white'
                            : 'from-violet-500/10 to-blue-500/10 dark:from-violet-500/15 dark:to-blue-500/15 text-violet-600 dark:text-violet-400 border border-violet-500/10'
                        }`}>
                          {team.name.charAt(0).toUpperCase()}
                        </div>
                        <span className="truncate">{team.name}</span>
                      </div>
                      {isActive && <Check className="h-3.5 w-3.5 text-white flex-shrink-0" />}
                    </button>
                  );
                })}
              </div>
              <div className="border-t border-slate-100 dark:border-slate-800/80 mt-1 pt-1.5 pb-0.5">
                <button
                  type="button"
                  onClick={handleNavigateToTeams}
                  className="w-full flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-left text-[11px] font-bold text-violet-605 dark:text-violet-400 hover:bg-violet-500/10 transition-all cursor-pointer"
                >
                  <Users className="h-3.5 w-3.5" />
                  Manage Workspaces &rarr;
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
