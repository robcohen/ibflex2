import unittest
from ibflex import parser

class TestEquitySummaryNewFields(unittest.TestCase):
    def test_new_fields_parsing(self):
        xml_data = b"""
<FlexQueryResponse queryName="Test" type="AF">
    <FlexStatements count="1">
        <FlexStatement accountId="U12345" fromDate="20230101" toDate="20230131" period="LastMonth" whenGenerated="20230201;120000">
            <EquitySummaryInBase>
                <EquitySummaryByReportDateInBase accountId="ACCOUNT_ID" acctAlias="" model="" currency="USD" reportDate="20230131" cash="0" cashLong="0" cashShort="0" brokerCashComponent="0" brokerCashComponentLong="0" brokerCashComponentShort="0" fdicInsuredBankSweepAccountCashComponent="0" fdicInsuredBankSweepAccountCashComponentLong="0" fdicInsuredBankSweepAccountCashComponentShort="0" insuredBankDepositRedemptionCashComponent="0" insuredBankDepositRedemptionCashComponentLong="0" insuredBankDepositRedemptionCashComponentShort="0" slbCashCollateral="0" slbCashCollateralLong="0" slbCashCollateralShort="0" stock="0" stockLong="0" stockShort="0" ipoSubscription="0" ipoSubscriptionLong="0" ipoSubscriptionShort="0" slbDirectSecuritiesBorrowed="0" slbDirectSecuritiesBorrowedLong="0" slbDirectSecuritiesBorrowedShort="0" slbDirectSecuritiesLent="0" slbDirectSecuritiesLentLong="0" slbDirectSecuritiesLentShort="0" options="0" optionsLong="0" optionsShort="0" bonds="0" bondsLong="0" bondsShort="0" commodities="0" commoditiesLong="0" commoditiesShort="0" notes="0" notesLong="0" notesShort="0" funds="0" fundsLong="0" fundsShort="0" dividendAccruals="0" dividendAccrualsLong="0" dividendAccrualsShort="0" liteSurchargeAccruals="0" liteSurchargeAccrualsLong="0" liteSurchargeAccrualsShort="0" cgtWithholdingAccruals="0" cgtWithholdingAccrualsLong="0" cgtWithholdingAccrualsShort="0" interestAccruals="0" interestAccrualsLong="0" interestAccrualsShort="0" incentiveCouponAccruals="0" incentiveCouponAccrualsLong="0" incentiveCouponAccrualsShort="0" brokerInterestAccrualsComponent="0" brokerInterestAccrualsComponentLong="0" brokerInterestAccrualsComponentShort="0" fdicInsuredAccountInterestAccrualsComponent="0" fdicInsuredAccountInterestAccrualsComponentLong="0" fdicInsuredAccountInterestAccrualsComponentShort="0" bondInterestAccrualsComponent="0" bondInterestAccrualsComponentLong="0" bondInterestAccrualsComponentShort="0" brokerFeesAccrualsComponent="0" brokerFeesAccrualsComponentLong="0" brokerFeesAccrualsComponentShort="0" eventContractInterestAccruals="0" eventContractInterestAccrualsLong="0" eventContractInterestAccrualsShort="0" marginFinancingChargeAccruals="0" marginFinancingChargeAccrualsLong="0" marginFinancingChargeAccrualsShort="0" softDollars="0" softDollarsLong="0" softDollarsShort="0" forexCfdUnrealizedPl="0" forexCfdUnrealizedPlLong="0" forexCfdUnrealizedPlShort="0" cfdUnrealizedPl="0" cfdUnrealizedPlLong="0" cfdUnrealizedPlShort="0" physDel="0" physDelLong="0" physDelShort="0" crypto="0" cryptoLong="0" cryptoShort="0" total="0" totalLong="0" totalShort="0" />
            </EquitySummaryInBase>
        </FlexStatement>
    </FlexStatements>
</FlexQueryResponse>
"""
        try:
            response = parser.parse(xml_data)
            self.assertIsInstance(response, parser.Types.FlexQueryResponse)

            equity_summary = response.FlexStatements[0].EquitySummaryInBase[0]

            # Check the new fields
            self.assertEqual(equity_summary.liteSurchargeAccrualsLong, 0)
            self.assertEqual(equity_summary.liteSurchargeAccrualsShort, 0)
            self.assertEqual(equity_summary.cgtWithholdingAccruals, 0)
            self.assertEqual(equity_summary.cgtWithholdingAccrualsLong, 0)
            self.assertEqual(equity_summary.cgtWithholdingAccrualsShort, 0)

            print("\nSuccessfully parsed XML data and verified new fields")
        except parser.FlexParserError as e:
            self.fail(f"FlexParserError raised: {e}")

if __name__ == '__main__':
    unittest.main()
