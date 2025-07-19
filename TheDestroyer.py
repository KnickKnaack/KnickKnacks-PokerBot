import json
import multiprocessing
import random
import time
from collections import Counter
import math
import itertools


# Import possible actions
from board import (
    CallAction,
    Card,
    CheckAction,
    Deck,
    FoldAction,
    RaiseAction,
    evaluate_hand,
)




class PokerBot(multiprocessing.Process):
    def __init__(self, conn, name="Knicks Knacker"):
        super().__init__()
        self.conn = conn
        self.running = True
        self.name = name
        self.action_count = 0

    def run(self):
        print(f"[{self.name}] Starting bot process...")
        while self.running:
            if self.conn.poll():  # Check for incoming message
                msg = self.conn.recv()
                if msg == "terminate":
                    self.running = False
                    print(f"[{self.name}] Terminating bot process...")
                else:
                    # Assume msg is the game state JSON
                    action = self.decide_action(msg)
                    self.conn.send(action)
            time.sleep(0.01)  # Prevent CPU overuse

    def decide_action(self, game_state_json):
        self.action_count += 1
        game_state = json.loads(game_state_json)
        is_end_state = game_state.get("is_end_state", bool)
        if is_end_state:
            self.end_game(game_state_json)

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
        draws_left = 5 - len(board)

        ############
        if pot > 0:
            pot_odds = curr_bet / (pot + curr_bet - player_curr_bet)
        else:
            pot_odds = 1

        

        # very hard to read logic
        # but basically if hand has OK odds or has a decent hand already, raise, otherwise call.
        # if hand has low odds and doesn't already have a ok hand, fold if bet was raised at all.

        # if draws_left <= 2:
        #     score = evaluate_hand(board + hand)[0][0]
        #     if score > 2:
        #         if score > 4:
        #             # print("has good hand")
        #             if curr_bet < player_curr_chips // 2:
        #                 return RaiseAction(player_curr_chips // 2)
        #             return CallAction()
        #         # print("has ok hand")
        #         if int(curr_bet * 0.5) < player_curr_chips // 2:
        #             RaiseAction(int(curr_bet * 0.5))
        #         return CallAction()
        #     # print(f"in last draws, score = {score}, draws = {draws_left}")
        #     if draws_left == 0 and score >= 1:
        #         return CallAction()

        # if player_curr_chips < ante * 2:
        #     # print("desperate all in")
        #     # print(f"current stack: {player_stack}, ante: {ante}")
        #     return CallAction()
        # if      (
        #             flush_odds(hand, board) <= 0.5
        #             and three_odds(hand, board) <= 0.4
        #             and draws_left <= 1
        #         ):
        #     # print("bad odds")
        #     if curr_bet - player_curr_bet == 0:
        #         return CallAction()
        #     return FoldAction()
        # if (
        #         flush_odds(hand, board) >= 0.5
        #         or three_odds(hand, board) >= 0.6
        #         or quad_odds(hand, board) >= 0.2
        #     ):
        #     # print("good odds")
        #     if player_curr_chips // 10 > curr_bet:
        #         return RaiseAction(player_curr_chips // 10)
        #     if player_curr_chips > curr_bet - player_curr_bet:
        #         return CallAction()
        # if curr_bet - player_curr_bet <= player_curr_chips // 10 or draws_left >= 2:
        #     # print("small bet, calling")
        #     return CallAction()
        # # print(f"curr_bet: {curr_bet}, player_curr_bet: {player_curr_bet}")
        # # print("############### Bot is confuzed")
        return FoldAction()

    def end_game(self, game_state_json):
        # Handle end of round state
        # game state will show final round standings and each
        # players last action
        pass



class PokerProbabilities():
    #Constants
    TOTAL_GAME_CARDS = 7
    FLUSH_CARDS_NEEDED = 5

    cardsInDeck = Deck().cards
    leftToDraw = TOTAL_GAME_CARDS
    currCards = []


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




def flush_probability_with_hand(current_hand, num_drawn=7, flush_size=5, num_suits=4, cards_per_suit=13):
    suits = ['H', 'S', 'D', 'C'][:num_suits]
    suit_counter = Counter(current_hand)

    cards_in_hand = len(current_hand)
    cards_to_draw = num_drawn - cards_in_hand
    total_cards_remaining = num_suits * cards_per_suit - cards_in_hand

    # If already have flush, guaranteed
    if any(suit_counter[suit] >= flush_size for suit in suits):
        return 1.0

    total_ways = math.comb(total_cards_remaining, cards_to_draw)
    flush_prob = 0.0

    for suit in suits:
        current_count = suit_counter[suit]
        needed = flush_size - current_count
        if needed > cards_to_draw or needed > cards_per_suit - current_count:
            continue

        max_possible_from_suit = min(cards_per_suit - current_count, cards_to_draw)
        ways = 0

        # Sum over the number of cards of the target suit drawn to reach flush
        for k in range(needed, max_possible_from_suit + 1):
            ways_suit = math.comb(cards_per_suit - current_count, k)
            ways_other = math.comb(total_cards_remaining - (cards_per_suit - current_count), cards_to_draw - k)
            ways += ways_suit * ways_other

        flush_prob += ways / total_ways

    # Cap at 1 in case of numerical floating overrun
    return min(flush_prob, 1.0)


def test():
    

    probs = PokerProbabilities()

    # chance = 1
    # while (chance != 0):
    #     deck = Deck()
    #     deck.shuffle()

    #     probs.reset_deck()

    #     hand = deck.deal(2)
    #     board = deck.deal(3)

    #     probs.add_to_hand(hand + board)

    #     chance = probs.flush_odds()

    # print(hand+ board)


    deck = Deck()
    deck.shuffle()
    # hand = deck.deal(2)
    # board = deck.deal()
    # print(type([(1, 2), (3, 4)][0]))
    # print(type([[(1, 2), (3, 4)],[(1, 2), (3, 4)]][0]))
    
    hand = [Card('Hearts', '4'), Card('Hearts', '5'), Card('Hearts', '6'), Card('Hearts', '7'),Card('Spades', '4')]
    # hand = [Card('Hearts', '4'), Card('Hearts', '5'), Card('Hearts', '6'), Card('Clubs', '7'),Card('Spades', '4')]
    # hand = []
    board = []

    probs.take_from_deck(hand + board)


    print(probs.currCards)
    print('mine:', probs.flush_odds())
    current_hand = ['H']
    print('geeps:', flush_probability_with_hand(current_hand, num_drawn=14))
    
    print('reg:', 1 - (38*37)/(47*46))
    print('4 needed:', 1 - (37*36)/(47*46))

    


