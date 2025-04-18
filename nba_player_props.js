const axios = require('axios');

const API_KEY = 'd5fc1dff6519aedb48fee57ec75af13d';
const SPORT = 'basketball_nba';
const MARKET = 'player_points';
const REGIONS = 'us';
const ODDS_FORMAT = 'american';

/**
 * Fetches NBA player props for points from The Odds API
 */
async function fetchNBAPlayerPointsProps() {
  try {
    console.log('Fetching NBA player points props...');
    
    const url = `https://api.the-odds-api.com/v4/sports/${SPORT}/odds`;
    const response = await axios.get(url, {
      params: {
        apiKey: API_KEY,
        regions: REGIONS,
        markets: MARKET,
        oddsFormat: ODDS_FORMAT
      }
    });

    const games = response.data;
    console.log(`Found ${games.length} NBA games with player points props`);
    
    // Process and display the data
    games.forEach(game => {
      console.log(`\n${game.away_team} @ ${game.home_team} - ${new Date(game.commence_time).toLocaleString()}`);
      
      game.bookmakers.forEach(bookmaker => {
        console.log(`\n  Bookmaker: ${bookmaker.title}`);
        
        const playerPointsMarket = bookmaker.markets.find(market => market.key === MARKET);
        if (playerPointsMarket) {
          console.log(`  Last Updated: ${new Date(playerPointsMarket.last_update).toLocaleString()}`);
          
          playerPointsMarket.outcomes.forEach(outcome => {
            const price = outcome.price > 0 ? `+${outcome.price}` : outcome.price;
            console.log(`    ${outcome.name}: Over/Under ${outcome.point} (${price})`);
          });
        } else {
          console.log('  No player points props available');
        }
      });
    });

    return games;
  } catch (error) {
    console.error('Error fetching NBA player points props:', error.message);
    if (error.response) {
      console.error('API Response:', error.response.data);
      console.error('Status:', error.response.status);
    }
    throw error;
  }
}

// Execute the function
fetchNBAPlayerPointsProps()
  .then(() => console.log('Done!'))
  .catch(err => console.error('Failed to fetch data:', err)); 