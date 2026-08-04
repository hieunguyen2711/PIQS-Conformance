/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.smartwallet;

/**
 *
 * @author kim2
 */
public class SmartWallet {

    public static void main(String[] args) {
        User user = new User("John Doe", "123456");
        if (user.authenticate("123456")) {
            user.addWallet("USD");
            user.addWallet("EUR");

            Wallet usdWallet = user.getWallet("USD");
            Wallet eurWallet = user.getWallet("EUR");

            usdWallet.addFunds(100);  // Add $100 to the USD wallet
            usdWallet.makePayment(25);  // Make a payment of $25 from USD wallet
            eurWallet.addFunds(200);  // Add €200 to the EUR wallet

            double convertedAmount = CurrencyConverter.convert("EUR", "USD", 50);
            System.out.println("Converted €50 to $" + convertedAmount);

            user.showAllBalances();  // Show balances for all wallets
            usdWallet.showTransactions();  // Print USD wallet transaction history
            eurWallet.showTransactions();  // Print EUR wallet transaction history
        }
    }
}
