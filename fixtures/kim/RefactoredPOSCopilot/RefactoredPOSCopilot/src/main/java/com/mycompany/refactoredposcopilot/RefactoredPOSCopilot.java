/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.refactoredposcopilot;

import java.text.DecimalFormat;
import java.util.Scanner;

/**
 *
 * @author kim2
 */
public class RefactoredPOSCopilot {

    static POS p;

    public static void main(String[] args) throws Exception {
        DecimalFormat dfMoney = new DecimalFormat("$##.00");
        Scanner scan = new Scanner(System.in);

        System.out.println("Start");
        p = new POS();

        Item i1 = new Item(1, "Milk  ", 3.79);
        Item i2 = new Item(2, "Banana", 1.49);
        Item i3 = new Item(3, "Apple ", 5.56);

        p.addInventory(i1, 10);
        p.addInventory(i2, 50);
        p.addInventory(i3, 30);

        System.out.println("\nStarting Sale Process\n");
        p.processSale();

        System.out.println("\nEntering items\n");
        System.out.println("  Item\t\tQuantity\tPrice");
        System.out.println("_______________________________________");

        p.enterItem(i1, 2);
        p.enterItem(i2, 3);
        p.enterItem(i3, 1);

        double total = p.getTotal();
        System.out.println("\nTotal: " + dfMoney.format(total));

        System.out.println("\nSelect Payment method (cash/credit card):");
        String paymentType = scan.nextLine();
        System.out.println("\n" + p.makePayment(total, paymentType));
    }
}
