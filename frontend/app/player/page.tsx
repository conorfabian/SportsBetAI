"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import PlayerSearch from "../components/PlayerSearch";

interface PlayerProp {
  player: {
    id: number;
    name: string;
    team: string;
  };
  game: {
    date: string;
    time: string | null;
    home_team: string;
    away_team: string;
    matchup: string;
  };
  prop: {
    id: number;
    line: number;
    sportsbook: string;
    fetched_at: string;
  };
  stats: {
    recent_games: Array<{
      game_date: string;
      matchup: string;
      points: number;
      minutes: number | string;
      field_goals: string;
      field_goal_pct: number | null;
    }>;
    season_avg_points: number | null;
    season_avg_minutes: number | null;
    games_played: number;
  };
  prediction?: {
    prob_over: number;
    confidence_interval: number;
    generated_at: string;
  };
}

export default function PlayerPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [playerData, setPlayerData] = useState<PlayerProp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const playerName = searchParams.get("name");
  const date = searchParams.get("date") || new Date().toISOString().split("T")[0];
  
  useEffect(() => {
    if (!playerName) {
      router.push("/");
      return;
    }
    
    fetchPlayerProp();
  }, [playerName, date]);
  
  const fetchPlayerProp = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'}/api/props/player?name=${encodeURIComponent(playerName || "")}&date=${date}`
      );
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`No prop found for ${playerName} on this date`);
        }
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setPlayerData(data);
    } catch (err: any) {
      console.error("Failed to fetch player prop:", err);
      setError(err.message || "Failed to load player data");
    } finally {
      setLoading(false);
    }
  };

  // Function to format probability as percentage
  const formatProbability = (prob: number) => {
    return `${(prob * 100).toFixed(1)}%`;
  };
  
  // Function to determine probability badge color
  const getProbabilityBadgeClass = (prob: number) => {
    if (prob >= 0.7) return "bg-emerald-100 text-emerald-800 border-emerald-500";
    if (prob >= 0.5) return "bg-amber-100 text-amber-800 border-amber-500";
    return "bg-rose-100 text-rose-800 border-rose-500";
  };

  // Function to format date
  const formatDate = (dateString: string) => {
    const options: Intl.DateTimeFormatOptions = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-4 md:p-8">
      <div className="w-full max-w-4xl">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
          <Link href="/" className="text-blue-500 hover:text-blue-700 mb-4 md:mb-0 flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to All Props
          </Link>
          <PlayerSearch className="md:w-64" />
        </div>
        
        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="w-12 h-12 border-4 border-t-blue-500 border-b-blue-700 rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600">Loading player data...</p>
          </div>
        )}
        
        {/* Error State */}
        {error && !loading && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <p>{error}</p>
            <button 
              onClick={fetchPlayerProp}
              className="mt-2 bg-red-700 text-white px-4 py-1 rounded hover:bg-red-800"
            >
              Try Again
            </button>
            <Link href="/" className="mt-2 ml-2 bg-gray-500 text-white px-4 py-1 rounded hover:bg-gray-600 inline-block">
              Back to Home
            </Link>
          </div>
        )}
        
        {/* Player Data */}
        {!loading && !error && playerData && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            {/* Player Header */}
            <div className="bg-gray-50 dark:bg-gray-700 px-6 py-4">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center">
                <div>
                  <h1 className="text-2xl font-bold">{playerData.player.name}</h1>
                  <p className="text-gray-600 dark:text-gray-400">{playerData.player.team}</p>
                </div>
                <div className="mt-2 md:mt-0">
                  <span className="inline-block bg-gray-200 dark:bg-gray-600 rounded-full px-3 py-1 text-sm font-semibold">
                    {playerData.game.matchup} • {formatDate(playerData.game.date)}
                  </span>
                </div>
              </div>
            </div>
            
            {/* Prop Details */}
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Prop and Prediction */}
              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <h2 className="text-lg font-semibold mb-3">Points Prop</h2>
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">Line</p>
                    <p className="text-2xl font-bold">{playerData.prop.line.toFixed(1)}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">Prediction</p>
                    {playerData.prediction ? (
                      <div className="flex items-center">
                        <span 
                          className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getProbabilityBadgeClass(playerData.prediction.prob_over)}`}
                          title={`Confidence interval: ±${playerData.prediction.confidence_interval.toFixed(1)}%`}
                        >
                          {formatProbability(playerData.prediction.prob_over)}
                        </span>
                      </div>
                    ) : (
                      <p className="text-gray-500">No prediction available</p>
                    )}
                  </div>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  <p>Sportsbook: {playerData.prop.sportsbook}</p>
                  {playerData.prediction && (
                    <p className="mt-1">
                      {playerData.prediction.prob_over >= 0.5 ? "OVER" : "UNDER"} recommended
                      {playerData.prediction.prob_over >= 0.7 || playerData.prediction.prob_over <= 0.3 ? " (strong)" : ""}
                    </p>
                  )}
                </div>
              </div>
              
              {/* Season Stats */}
              <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                <h2 className="text-lg font-semibold mb-3">Season Stats</h2>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">PPG</p>
                    <p className="text-2xl font-bold">{playerData.stats.season_avg_points?.toFixed(1) || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">MPG</p>
                    <p className="text-2xl font-bold">{playerData.stats.season_avg_minutes?.toFixed(1) || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">Games</p>
                    <p className="text-2xl font-bold">{playerData.stats.games_played}</p>
                  </div>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-4">
                  Prop line vs. season average: 
                  {playerData.stats.season_avg_points ? (
                    playerData.prop.line > playerData.stats.season_avg_points 
                      ? <span className="text-red-500 ml-1">{(playerData.prop.line - playerData.stats.season_avg_points).toFixed(1)} over avg</span>
                      : <span className="text-green-500 ml-1">{(playerData.stats.season_avg_points - playerData.prop.line).toFixed(1)} under avg</span>
                  ) : 'N/A'}
                </p>
              </div>
              
              {/* Recent Games */}
              <div className="md:col-span-2">
                <h2 className="text-lg font-semibold mb-3">Recent Games</h2>
                <div className="overflow-x-auto">
                  <table className="min-w-full bg-white dark:bg-gray-800 rounded-lg overflow-hidden">
                    <thead className="bg-gray-100 dark:bg-gray-700">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Date</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Matchup</th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Minutes</th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Points</th>
                        <th className="px-4 py-2 text-center text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">FG</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {playerData.stats.recent_games.map((game, index) => (
                        <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                          <td className="px-4 py-2 whitespace-nowrap text-xs">
                            {formatDate(game.game_date)}
                          </td>
                          <td className="px-4 py-2 whitespace-nowrap text-xs">
                            {game.matchup}
                          </td>
                          <td className="px-4 py-2 whitespace-nowrap text-center text-xs">
                            {typeof game.minutes === 'number' ? game.minutes.toFixed(1) : game.minutes}
                          </td>
                          <td className={`px-4 py-2 whitespace-nowrap text-center text-xs font-medium ${
                            game.points > playerData.prop.line ? 'text-green-600' : 
                            game.points < playerData.prop.line ? 'text-red-600' : ''
                          }`}>
                            {game.points}
                          </td>
                          <td className="px-4 py-2 whitespace-nowrap text-center text-xs">
                            {game.field_goals}
                            {game.field_goal_pct !== null && (
                              <span className="ml-1 text-gray-500">({(game.field_goal_pct * 100).toFixed(1)}%)</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            
            {/* Disclaimer */}
            <div className="px-6 py-3 bg-gray-50 dark:bg-gray-700 text-xs text-gray-500 dark:text-gray-400">
              Last updated: {playerData.prediction ? new Date(playerData.prediction.generated_at).toLocaleString() : 'N/A'}
            </div>
          </div>
        )}
      </div>
    </main>
  );
} 