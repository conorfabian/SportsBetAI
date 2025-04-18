from nba_api.stats.endpoints import playergamelog
import pandas as pd

# Nikola Jokić's player ID
JOKIC_ID = 203999

def get_jokic_gamelog():
    # Fetch Jokić's game log for the 2024-25 season
    # Note: The season format is YYYY-YY (e.g., 2024-25)
    gamelog = playergamelog.PlayerGameLog(
        player_id=JOKIC_ID,
        season='2024-25',  # 2024-25 season
        season_type_all_star='Regular Season'
    )
    
    # Convert to DataFrame
    df = gamelog.get_data_frames()[0]
    
    # Display basic stats
    print(f"Total games played: {len(df)}")
    print("\nLast 5 games:")
    
    # Select important columns for display
    display_cols = ['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FG3_PCT', 'FT_PCT']
    
    # Show last 5 games (most recent first)
    print(df[display_cols].head(5).to_string(index=False))
    
    # Save to CSV
    df.to_csv('jokic_2024_25_gamelog.csv', index=False)
    print("\nComplete game log saved to 'jokic_2024_25_gamelog.csv'")
    
    return df

if __name__ == "__main__":
    try:
        jokic_games = get_jokic_gamelog()
    except Exception as e:
        # If season hasn't started yet or there's another error
        print(f"Error fetching data: {e}")
        print("Note: If you're getting a 400 error, the 2024-25 season data may not be available yet.") 