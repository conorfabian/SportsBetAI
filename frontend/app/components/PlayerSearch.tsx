"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

interface PlayerSearchProps {
  className?: string;
}

interface Player {
  id: number;
  name: string;
}

export default function PlayerSearch({ className = "" }: PlayerSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Player[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    // Add click outside listener to close results
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  useEffect(() => {
    // Debounce function to delay API calls while typing
    const delayDebounceFn = setTimeout(() => {
      if (query.length >= 2) {
        searchPlayers();
      } else {
        setResults([]);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [query]);

  const searchPlayers = async () => {
    if (!query || query.length < 2) return;
    
    setIsLoading(true);
    
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'}/api/props/players/search?q=${encodeURIComponent(query)}`
      );
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.status === 'success' && data.players) {
        setResults(data.players.map((p: any) => ({ id: p.id, name: p.name })));
        setShowResults(true);
      } else {
        setResults([]);
      }
    } catch (err) {
      console.error("Failed to search players:", err);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const handleSelectPlayer = (player: Player) => {
    setQuery("");
    setShowResults(false);
    router.push(`/player?name=${encodeURIComponent(player.name)}`);
  };

  return (
    <div ref={searchRef} className={`relative ${className}`}>
      <div className="relative">
        <input
          type="text"
          placeholder="Search for a player..."
          value={query}
          onChange={handleInputChange}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2 pr-10 focus:outline-none focus:ring-2 focus:ring-blue-500"
          onFocus={() => query.length >= 2 && setShowResults(true)}
        />
        <div className="absolute right-3 top-2.5">
          {isLoading ? (
            <div className="h-5 w-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
          ) : (
            <svg
              className="h-5 w-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          )}
        </div>
      </div>

      {/* Search Results Dropdown */}
      {showResults && (
        <div className="absolute z-10 mt-1 w-full rounded-md bg-white dark:bg-gray-800 shadow-lg max-h-60 overflow-auto">
          {results.length > 0 ? (
            <ul className="py-1">
              {results.map((player) => (
                <li
                  key={player.id}
                  className="px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer"
                  onClick={() => handleSelectPlayer(player)}
                >
                  {player.name}
                </li>
              ))}
            </ul>
          ) : (
            query.length >= 2 && (
              <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                No players found
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
} 