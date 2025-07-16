import json
import multiprocessing
import random
import time
from collections import Counter
import math


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

        if draws_left <= 2:
            score = evaluate_hand(board + hand)[0][0]
            if score > 2:
                if score > 4:
                    # print("has good hand")
                    if curr_bet < player_curr_chips // 2:
                        return RaiseAction(player_curr_chips // 2)
                    return CallAction()
                # print("has ok hand")
                if int(curr_bet * 0.5) < player_curr_chips // 2:
                    RaiseAction(int(curr_bet * 0.5))
                return CallAction()
            # print(f"in last draws, score = {score}, draws = {draws_left}")
            if draws_left == 0 and score >= 1:
                return CallAction()

        if player_curr_chips < ante * 2:
            # print("desperate all in")
            # print(f"current stack: {player_stack}, ante: {ante}")
            return CallAction()
        if      (
                    flush_odds(hand, board) <= 0.5
                    and three_odds(hand, board) <= 0.4
                    and draws_left <= 1
                ):
            # print("bad odds")
            if curr_bet - player_curr_bet == 0:
                return CallAction()
            return FoldAction()
        if (
                flush_odds(hand, board) >= 0.5
                or three_odds(hand, board) >= 0.6
                or quad_odds(hand, board) >= 0.2
            ):
            # print("good odds")
            if player_curr_chips // 10 > curr_bet:
                return RaiseAction(player_curr_chips // 10)
            if player_curr_chips > curr_bet - player_curr_bet:
                return CallAction()
        if curr_bet - player_curr_bet <= player_curr_chips // 10 or draws_left >= 2:
            # print("small bet, calling")
            return CallAction()
        # print(f"curr_bet: {curr_bet}, player_curr_bet: {player_curr_bet}")
        # print("############### Bot is confuzed")
        return FoldAction()

    def end_game(self, game_state_json):
        # Handle end of round state
        # game state will show final round standings and each
        # players last action
        pass



class PokerProbabilities():
    cardsInDeck = Deck().cards
    TOTAL_GAME_CARDS = 7
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

    def evaluate_combinations(self, choices):
        probability = math.prod(list(map(self.nCr, choices))) / (self.nCr((len(self.cardsInDeck), self.leftToDraw))) 

        return probability
        


    def reset_deck(self):
        self.cardsInDeck = Deck().cards
        self.leftToDraw = self.TOTAL_GAME_CARDS
        self.currCards = []

    def add_to_hand(self, toAdd):
        d = self.cardsInDeck
        for c in toAdd:
            d.remove(c)

        self.currCards += toAdd

        self.leftToDraw = self.leftToDraw - len(toAdd)


    def flush_odds(self):
        suits = [card.suit for card in self.currCards]
        suit_counts = Counter(suits)
        print('my suit coutns', suit_counts)

        

        deck_suits = [card.suit for card in self.cardsInDeck]
        deck_suit_counts = Counter(deck_suits)
        print('deck suit counts', deck_suit_counts)

        chance = 0


        
        for suit, count in suit_counts.items():
            excess = self.leftToDraw - (5 - count)
            if count == 5:
                return 1
            elif (excess) < 0:
                continue

            combinations = [(deck_suit_counts[suit], (5 - count)), (len(self.cardsInDeck) - deck_suit_counts[suit], excess)]
            print(combinations)
            chance = max(chance, self.evaluate_combinations(combinations)) 
            

        return chance

    def straight_odds(self, hand, board):
        all_cards = hand + board

        max_chance = 0

        return max_chance

    def pair_odds(self, hand, board):
        all_cards = hand + board
        ranks = [card.rank for card in all_cards]
        rank_counts = Counter(ranks)

        deck_ranks = [card.rank for card in self.cardsInDeck]
        deck_rank_counts = Counter(deck_ranks)

        for rank, count in rank_counts.items():
            if count == 2:
                return 1

        return 0.5

    def three_odds(self, hand, board):
        all_cards = hand + board
        ranks = [card.rank for card in all_cards]
        rank_counts = Counter(ranks)

        deck_ranks = [card.rank for card in self.cardsInDeck]
        deck_rank_counts = Counter(deck_ranks)

        max_rank = []
        max_count = 0
        for rank, count in rank_counts.items():
            if count == 3:
                return 1
            if count > max_count:
                max_count = count
                max_rank.append(rank)
            if count == max_count:
                max_rank.append(rank)
        odd = 0
        for rank in max_rank:
            odd += (deck_rank_counts[rank] / len(self.deck_left)) ** (3 - max_count)
        return 1 - ((1 - odd) ** self.cardsInDeck)

    def quad_odds(self, hand, board):
        all_cards = hand + board
        ranks = [card.rank for card in all_cards]
        rank_counts = Counter(ranks)

        deck_ranks = [card.rank for card in self.deck_left]
        deck_rank_counts = Counter(deck_ranks)

        max_rank = []
        max_count = 0
        for rank, count in rank_counts.items():
            if count == 4:
                return 1
            if count > max_count:
                max_count = count
                max_rank.append(rank)
            if count == max_count:
                max_rank.append(rank)
        odd = 0
        for rank in max_rank:
            odd += (deck_rank_counts[rank] / len(self.cardsInDeck)) ** (4 - max_count)
        return 1 - ((1 - odd) ** self.cardsInDeck)

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
    hand = deck.deal(2)
    board = deck.deal(3)
    
    hand = [Card('Hearts', '4'), Card('Hearts', '5'), Card('Hearts', '6'), Card('Hearts', '7'),Card('Spades', '4')]
    board = []

    probs.add_to_hand(hand + board)
    print(probs.currCards)
    # print(probs.cardsInDeck)
    print(probs.flush_odds())
    
    print(1 - (38*37)/(47*46))
    # print(probs.nCr((9, 1)))
    # print(probs.nCr((10, 2)))
    # print(probs.evalucate_choice([(9, 1)], 2))
    # print(probs.evalucate_choice([(10, 2)], 2))
    


