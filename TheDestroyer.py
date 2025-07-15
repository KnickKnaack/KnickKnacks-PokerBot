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
    cardsLeft = Deck()

    def update_cards_left(self, hand, board):
        d = Deck().cards
        for c in hand+board:
            d.remove(c)

        self.cardsLeft = d

    def flush_odds(self, hand, board):
            all_cards = hand + board
            suits = [card.suit for card in all_cards]
            suit_counts = Counter(suits)

            deck_suits = [card.suit for card in self.cardsLeft]
            deck_suit_counts = Counter(deck_suits)

            max_chance = 0

            for suit, count in suit_counts.items():
                if count == 5:
                    return 1
                # estimated chances of getting needed cards
                chanceOfNone = (len(self.cardsLeft) - deck_suit_counts[suit]) / len(self.cardsLeft)
                chance = math.factorial(chanceOfNone) / math.factorial(chanceOfNone - (5 - count))
                if chance > max_chance:
                    max_chance = chance
            return chance

    def straight_odds(self, hand, board):
        all_cards = hand + board

        max_chance = 0

        return max_chance

    def pair_odds(self, hand, board):
        all_cards = hand + board
        ranks = [card.rank for card in all_cards]
        rank_counts = Counter(ranks)

        deck_ranks = [card.rank for card in self.cardsLeft]
        deck_rank_counts = Counter(deck_ranks)

        for rank, count in rank_counts.items():
            if count == 2:
                return 1

        return 0.5

    def three_odds(self, hand, board):
        all_cards = hand + board
        ranks = [card.rank for card in all_cards]
        rank_counts = Counter(ranks)

        deck_ranks = [card.rank for card in self.cardsLeft]
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
        return 1 - ((1 - odd) ** self.cardsLeft)

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
            odd += (deck_rank_counts[rank] / len(self.cardsLeft)) ** (4 - max_count)
        return 1 - ((1 - odd) ** self.cardsLeft)

def test():
    deck = Deck()
    deck.shuffle()

    probs = PokerProbabilities()




    hand = deck.deal(48)
    board = deck.deal(2)

    print(hand + board)
    
    probs.update_cards_left(hand, board)

    print(probs.cardsLeft)
    


