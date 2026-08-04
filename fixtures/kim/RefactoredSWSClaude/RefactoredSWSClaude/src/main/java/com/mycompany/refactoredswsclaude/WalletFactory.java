/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredswsclaude;

/**
 *
 * @author kim2
 */
// -------------------- Factory Method Pattern Start --------------------
interface WalletFactory {
    Wallet createWallet(String currency);
}

