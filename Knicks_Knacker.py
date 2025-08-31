import json
import multiprocessing
import random
import time
from collections import Counter
import math
import itertools

import board

# Import possible actions
from board import (
    CallAction,
    Card,
    CheckAction,
    Deck,
    FoldAction,
    RaiseAction,
    evaluate_hand,
    hand_score,
    RANK_ORDER
)





class PokerBot(multiprocessing.Process):
    def __init__(self, conn, name="Knicks Knacker"):
        super().__init__()
        self.conn = conn
        self.running = True
        self.name = name
        self.probs = PokerProbabilities()
        self.playerManager = PlayerManager()

    def run(self):
        print(f"[{self.name}] Starting bot process...")
        while self.running:
            if self.conn.poll():  # Check for incoming message
                msg = self.conn.recv()
                if msg == "terminate":
                    self.running = False
                    print(f"[{self.name}] Terminating bot process...")
                else:
                    game_state = json.loads(msg)
                    if (game_state.get("is_end_state", False)):
                        #end game state
                        self.end_game(msg)

                    else:
                        #in-game state
                        action = self.decide_action(game_state)
                        self.conn.send(action)

            time.sleep(0.01)  # Prevent CPU overuse


    def decide_action(self, game_state):

        player_curr_bet = game_state.get("player_curr_bet", 0)
        board = game_state.get("board", [])
        board = [Card(suit=x["suit"], rank=x["rank"]) for x in board]
        hand = game_state.get("hand", [])
        hand = [Card(suit=x["suit"], rank=x["rank"]) for x in hand]
        # can_check = game_state.get("can_check", False)
        curr_bet = game_state.get("curr_bet", 0)
        ante = game_state.get("ante", 0)
        pot = game_state.get("pot", 0)
        players = game_state.get("players", {})
        player_curr_chips = players[self.name]["chips"]
        deck = Deck()

        score = self.probs.get_score()

        max_score = sum(self.probs.HAND_WEIGHTS)

        if (score / max_score > 0.10):
            return CallAction()
        elif ():
            pass
        else:
        
            return FoldAction()

    def end_game(self, game_state_json):
        # Handle end of round state
        # game state will show final round standings and each
        # players last action
        pass


class PlayerManager():
    players = {}




class PokerProbabilities():
    #Constants
    TOTAL_GAME_CARDS = 7
    FLUSH_CARDS_NEEDED = 5
    STRAIGHT_CARDS_NEEDED = 5
    DIFFERENT_RANK_TYPES = len(RANK_ORDER)

    cardsInDeck = Deck().cards
    leftToDraw = TOTAL_GAME_CARDS
    currCards: list[Card] = [] 

    HAND_WEIGHTS = [math.pow(1.75, (handRank + 1)/(2)) for handRank in range(len(hand_score))]

    RANK_WEIGHTS = {}

    MAX_RANK_VALUE = max(RANK_ORDER.values())
    for r, v in RANK_ORDER.items():
        RANK_WEIGHTS[r] = v/MAX_RANK_VALUE


    def blank():
        return 0


    def get_score(self):
        score = 0
        for i in range(len(self.probOrder)-1, -1, -1):
            prob = self.probOrder[i]
            score += prob * self.HAND_WEIGHTS[i]

            if prob == 1:
                break
            
        return score
            

    def nCr(self, NR):
        n, r = NR
        sum = 1

        # Calculate the value of n choose r 
        # using the binomial coefficient formula
        for i in range(1, r+1):
            sum = sum * (n - r + i) // i
    
        return sum

    def evaluate_combinations(self, choices, raw = None):
        if raw == None:
            total = (self.nCr((len(self.cardsInDeck), self.leftToDraw)))
        else:
            total = self.nCr(raw) 

        if (len(choices) <= 0):
            return 0
        elif (type(choices[0]) == list):
            probability = sum(map(lambda NRs : math.prod(map(self.nCr, NRs)), choices)) / total
        else:
            probability = math.prod(map(self.nCr, choices)) / total

    
        return probability
        


    def reset_deck(self):
        self.cardsInDeck = Deck().cards
        self.leftToDraw = self.TOTAL_GAME_CARDS
        self.currCards = []

    def take_from_deck(self, toTake, addToHand=True):
        d = self.cardsInDeck
        for c in toTake:
            d.remove(c)

        if (addToHand):
            self.currCards += toTake

            self.leftToDraw = self.leftToDraw - len(toTake)

    def straight_odds(self):
        currRanks = Counter([card.rank for card in self.currCards])

        numMissingRanks = [0] * (len(board.ranks) - self.STRAIGHT_CARDS_NEEDED + 2)

        i = 0

        while (i < self.STRAIGHT_CARDS_NEEDED):
            if board.ranks[i] not in currRanks:
                for straightIndex in range(i + 1):
                    numMissingRanks[straightIndex + 1] += 1
            i += 1
        

        while (i < len(board.ranks) - self.STRAIGHT_CARDS_NEEDED):
            if board.ranks[i] not in currRanks:
                for straightIndex in range(i-self.STRAIGHT_CARDS_NEEDED+1, i + 1):
                    numMissingRanks[straightIndex + 1] += 1
            i += 1
        i = len(board.ranks) - self.STRAIGHT_CARDS_NEEDED


        while (i < len(board.ranks)):
            if board.ranks[i] not in currRanks:
                for straightIndex in range(i-self.STRAIGHT_CARDS_NEEDED+1, len(numMissingRanks) - 1):
                    numMissingRanks[straightIndex + 1] += 1
            i += 1

        print(numMissingRanks)

        return 0
            

    def flush_odds(self):

        suits = [card.suit for card in self.currCards]
        suit_counts = Counter(suits)


        for suit in Card.SUIT_MAP.values():
            if suit not in suit_counts:
                suit_counts[suit] = 0


        deck_suits = [card.suit for card in self.cardsInDeck]
        deck_suit_counts = Counter(deck_suits)

        chance = 0


        for suit, count in suit_counts.items():
            cardsNeeded = (self.FLUSH_CARDS_NEEDED - count)
            excess = self.leftToDraw - cardsNeeded
            if count == self.FLUSH_CARDS_NEEDED:
                return 1
            elif (excess) < 0:
                continue

            #NOTE: The probabiliy of each suit is independant of eachother. (this may cause a slightly lower chance than actual in high-card cases)
            #   -ex: with 17 cards, a flush is gaurented
            # need to differentiate when you pick different amounts of the suit at hand
            #TODO: Flip this to inverse of the probabillity of not getting enough cards. (I think is more efficient?) (maybe do that for anything more than the minimum)
            combinations = [[(deck_suit_counts[suit], cardsNeeded + i), (len(self.cardsInDeck) - deck_suit_counts[suit], excess - i)] for i in range(excess + 1)]
            print(combinations)
            # chance = max(chance, self.evaluate_combinations(combinations))
            chance += self.evaluate_combinations(combinations)
            

        return chance
    
    def same_card_odds(self, sameNeeded):
        rank_counts = {rank:0 for rank in Card.REVERSE_RANK_MAP.keys()} 
        

        num_matches = 0
        max_match = 0

        for card in self.currCards:             

            rank_counts[card.rank] += 1
            if rank_counts[card.rank] == sameNeeded:
                num_matches += 1

                max_match = max(max_match, RANK_ORDER[card.rank])

                if num_matches == 2:
                    return 0
                
            elif rank_counts[card.rank] > sameNeeded:
                return 0
        
        if num_matches == 1:
            #minus one since 2 has value of 2 :/
            return ((max_match - 1) / self.DIFFERENT_RANK_TYPES)

        wheightedChance = 0


        for rank, count in rank_counts.items():
            if (sameNeeded - count > self.leftToDraw):
                continue
            combinations = [(4 - count, sameNeeded - count), (len(self.cardsInDeck) - (4 - count), self.leftToDraw - (sameNeeded - count))]
            # print(combinations)
            wheightedChance += self.evaluate_combinations(combinations) * self.RANK_WEIGHTS[rank]


        return wheightedChance


    def pair_odds(self):
        return self.same_card_odds(2)

    def three_of_a_kind_odds(self):
        return self.same_card_odds(3)

    def four_of_a_kind_odds(self):
        return self.same_card_odds(4)

    def pair_odds_old(self):
        rank_counts = {rank:0 for rank in Card.REVERSE_RANK_MAP.keys()} 
        

        num_pairs = 0
        max_pair = 0

        for card in self.currCards:             

            rank_counts[card.rank] += 1
            if rank_counts[card.rank] == 2:
                num_pairs += 1

                max_pair = max(max_pair, RANK_ORDER[card.rank])

                if num_pairs == 2:
                    return 0
                
            elif rank_counts[card.rank] > 2:
                return 0
        
        if num_pairs == 1:
            return ((max_pair - 1) / self.DIFFERENT_RANK_TYPES)

        wheightedChance = 0


        for rank, count in rank_counts.items():
            if (2 - count > self.leftToDraw):
                continue
            combinations = [(4 - count, 2 - count), (len(self.cardsInDeck) - (4 - count), self.leftToDraw - (2 - count))]

            wheightedChance += self.evaluate_combinations(combinations) * self.RANK_WEIGHTS[rank]


        return wheightedChance
    
    
    probOrder = [blank, 
                 pair_odds, 
                 blank, 
                 three_of_a_kind_odds, 
                 blank, 
                 flush_odds, 
                 blank, 
                 four_of_a_kind_odds,
                 blank]




def test():

    probs = PokerProbabilities()



    deck = Deck()
    deck.shuffle()
    # hand = deck.deal(2)
    # board = deck.deal()
    # print(type([(1, 2), (3, 4)][0]))
    # print(type([[(1, 2), (3, 4)],[(1, 2), (3, 4)]][0]))
    
    hand = [Card('Hearts', '8'), Card('Hearts', '9'), Card('Hearts', '10'), Card('Hearts', 'K')]
    hand = [Card('Hearts', 'A')]
    # hand = []
    # hand = [Card('Hearts', '4'), Card('Hearts', '5'), Card('Hearts', '6'), Card('Clubs', '7'),Card('Spades', '4')]
    # hand = []
    board = []

    probs.take_from_deck(hand + board)


    print(probs.straight_odds())


    


