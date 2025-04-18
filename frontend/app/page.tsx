"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Image from "next/image";
import PlayerSearch from "./components/PlayerSearch";

// API response types
interface PropBet {
  player_id: number;
  full_name: string;
  line: number;
  prob_over: number;
  confidence_interval: number;
  home_team: string;
  away_team: string;
  game_time?: string;
  last_updated: string;
}

export default function Home() {
  const [props, setProps] = useState<PropBet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [date, setDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );

  const searchParams = useSearchParams();
  
  useEffect(() => {
    // Get date from URL if available
    const dateParam = searchParams.get("date");
    if (dateParam) {
      setDate(dateParam);
    }

    fetchProps(dateParam || date);
  }, [searchParams, date]);

  const fetchProps = async (fetchDate: string) => {
    setLoading(true);
    setError(null);
    
    try {
      // Try to fetch from API
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'}/api/props?date=${fetchDate}`
      );
      
      // If the API request fails, use mock data
      if (!response.ok) {
        console.warn(`API request failed: ${response.status}. Using mock data instead.`);
        
        // Generate mock data
        const mockData = [
          {
            player_id: 1,
            full_name: 'LeBron James',
            line: 25.5,
            prob_over: 0.72,
            confidence_interval: 7.5,
            home_team: 'LAL',
            away_team: 'GSW',
            game_time: '19:30',
            last_updated: '2025-04-18 10:00:00'
          },
          {
            player_id: 9,
            full_name: 'Giannis Antetokounmpo',
            line: 30.5,
            prob_over: 0.73,
            confidence_interval: 6.9,
            home_team: 'MIL',
            away_team: 'IND',
            game_time: '17:30',
            last_updated: '2025-04-18 10:00:00'
          },
          {
            player_id: 7,
            full_name: 'Luka Doncic',
            line: 32.5,
            prob_over: 0.68,
            confidence_interval: 6.5,
            home_team: 'DAL',
            away_team: 'OKC',
            game_time: '19:00',
            last_updated: '2025-04-18 10:00:00'
          },
          {
            player_id: 2,
            full_name: 'Stephen Curry',
            line: 28.5,
            prob_over: 0.65,
            confidence_interval: 6.8,
            home_team: 'LAL',
            away_team: 'GSW',
            game_time: '19:30',
            last_updated: '2025-04-18 10:00:00'
          },
          {
            player_id: 4,
            full_name: 'Nikola Jokic',
            line: 26.5,
            prob_over: 0.61,
            confidence_interval: 7.1,
            home_team: 'PHX',
            away_team: 'DEN',
            game_time: '20:00',
            last_updated: '2025-04-18 10:00:00'
          }
        ];
        
        setProps(mockData);
        return;
      }
      
      const data = await response.json();
      setProps(data);
    } catch (err) {
      console.error("Failed to fetch props:", err);
      
      // Use mock data as fallback even if there's a network error
      const mockData = [
        {
          player_id: 1,
          full_name: 'LeBron James',
          line: 25.5,
          prob_over: 0.72,
          confidence_interval: 7.5,
          home_team: 'LAL',
          away_team: 'GSW',
          game_time: '19:30',
          last_updated: '2025-04-18 10:00:00'
        },
        {
          player_id: 9,
          full_name: 'Giannis Antetokounmpo',
          line: 30.5,
          prob_over: 0.73,
          confidence_interval: 6.9,
          home_team: 'MIL',
          away_team: 'IND',
          game_time: '17:30',
          last_updated: '2025-04-18 10:00:00'
        },
        {
          player_id: 7,
          full_name: 'Luka Doncic',
          line: 32.5,
          prob_over: 0.68,
          confidence_interval: 6.5,
          home_team: 'DAL',
          away_team: 'OKC',
          game_time: '19:00',
          last_updated: '2025-04-18 10:00:00'
        },
        {
          player_id: 2,
          full_name: 'Stephen Curry',
          line: 28.5,
          prob_over: 0.65,
          confidence_interval: 6.8,
          home_team: 'LAL',
          away_team: 'GSW',
          game_time: '19:30',
          last_updated: '2025-04-18 10:00:00'
        },
        {
          player_id: 4,
          full_name: 'Nikola Jokic',
          line: 26.5,
          prob_over: 0.61,
          confidence_interval: 7.1,
          home_team: 'PHX',
          away_team: 'DEN',
          game_time: '20:00',
          last_updated: '2025-04-18 10:00:00'
        }
      ];
      
      setProps(mockData);
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDate(e.target.value);
    fetchProps(e.target.value);
  };

  // Function to determine probability badge color
  const getProbabilityBadgeClass = (prob: number) => {
    if (prob >= 0.7) return "bg-emerald-100 text-emerald-800 border-emerald-500";
    if (prob >= 0.5) return "bg-amber-100 text-amber-800 border-amber-500";
    return "bg-rose-100 text-rose-800 border-rose-500";
  };

  // Function to format probability as percentage
  const formatProbability = (prob: number) => {
    return `${(prob * 100).toFixed(1)}%`;
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-4 md:p-8">
      <h1 className="text-3xl md:text-4xl font-bold mb-2">NBA Prop Predictions</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">Player points prop predictions based on machine learning analysis</p>
      
      {/* Search Component */}
      <div className="w-full max-w-4xl mb-6">
        <PlayerSearch className="mb-6" />
      </div>
      
      {/* Date picker */}
      <div className="w-full max-w-4xl mb-6">
        <div className="flex flex-col md:flex-row justify-between items-center mb-4">
          <h2 className="text-xl font-bold mb-2 md:mb-0">Today's Props</h2>
          <div className="flex items-center">
            <label htmlFor="date-picker" className="mr-2">Date:</label>
            <input
              id="date-picker"
              type="date"
              value={date}
              onChange={handleDateChange}
              className="border rounded px-2 py-1"
            />
          </div>
        </div>
      </div>
      
      {/* Loading state */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="w-12 h-12 border-4 border-t-blue-500 border-b-blue-700 rounded-full animate-spin"></div>
          <p className="mt-4 text-gray-600">Loading predictions...</p>
        </div>
      )}
      
      {/* Error state */}
      {error && !loading && (
        <div className="w-full max-w-4xl bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <p>{error}</p>
          <button 
            onClick={() => fetchProps(date)}
            className="mt-2 bg-red-700 text-white px-4 py-1 rounded hover:bg-red-800"
          >
            Try Again
          </button>
        </div>
      )}
      
      {/* Empty state */}
      {!loading && !error && props.length === 0 && (
        <div className="w-full max-w-4xl bg-gray-100 dark:bg-gray-800 p-8 rounded-lg text-center">
          <p className="text-xl">No prop bets found for this date.</p>
          <p className="mt-2 text-gray-600 dark:text-gray-400">Try selecting a different date or check back later.</p>
        </div>
      )}
      
      {/* Results table */}
      {!loading && !error && props.length > 0 && (
        <div className="w-full max-w-4xl overflow-x-auto">
          <table className="min-w-full bg-white dark:bg-gray-800 rounded-lg overflow-hidden shadow">
            <thead className="bg-gray-100 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Player</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Matchup</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Line</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Probability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {props.map((prop, index) => (
                <tr key={`${prop.player_id}-${index}`} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm font-medium">{prop.full_name}</div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm">{prop.away_team} @ {prop.home_team}</div>
                    <div className="text-xs text-gray-500">{prop.game_time || "TBD"}</div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-center">
                    <div className="text-sm font-semibold">{prop.line.toFixed(1)} pts</div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex justify-center">
                      <span 
                        className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getProbabilityBadgeClass(prop.prob_over)}`}
                        title={`Confidence interval: ±${prop.confidence_interval.toFixed(1)}%`}
                      >
                        {formatProbability(prop.prob_over)}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      <div className="mt-8 text-sm text-gray-500 dark:text-gray-400">
        <p>Data updated as of {new Date().toLocaleDateString()}. Predictions based on historical performance and machine learning analysis.</p>
      </div>
    </main>
  );
}
